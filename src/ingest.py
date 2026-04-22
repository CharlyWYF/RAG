from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path
from typing import Any, Callable

ProgressCallback = Callable[[str, float | None], None]

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import load_settings

SECTION_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _extract_source(metadata: dict | None) -> str:
    if not isinstance(metadata, dict):
        return ""
    source = metadata.get("source")
    if source is None:
        return ""
    return str(source).strip()


def _extract_source_hash(metadata: dict | None) -> str:
    if not isinstance(metadata, dict):
        return ""
    source_hash = metadata.get("source_hash")
    if source_hash is None:
        return ""
    return str(source_hash).strip()


def _source_key(source: str) -> str:
    return source.strip().replace("\\", "/").lower()


def _doc_source_key(doc: Any) -> str:
    source = _extract_source(getattr(doc, "metadata", None))
    if not source:
        return ""
    return _source_key(source)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_current_source_hashes(docs: list[Any]) -> dict[str, str]:
    source_hash_by_key: dict[str, str] = {}

    for doc in docs:
        source = _extract_source(getattr(doc, "metadata", None))
        if not source:
            continue
        key = _source_key(source)
        content = getattr(doc, "page_content", "")
        if not isinstance(content, str):
            content = str(content)
        source_hash_by_key[key] = _hash_text(content)

    return source_hash_by_key


def _load_existing_state(db: Chroma) -> tuple[dict[str, str], dict[str, set[str]]]:
    rows = db.get(include=["metadatas"])
    metadatas = rows.get("metadatas", [])

    source_hash_by_key: dict[str, str] = {}
    source_variants_by_key: dict[str, set[str]] = {}

    for metadata in metadatas:
        source = _extract_source(metadata)
        if not source:
            continue

        key = _source_key(source)
        source_variants_by_key.setdefault(key, set()).add(source)

        source_hash = _extract_source_hash(metadata)
        if key not in source_hash_by_key:
            source_hash_by_key[key] = source_hash
            continue

        existing_hash = source_hash_by_key[key]
        if not existing_hash and source_hash:
            source_hash_by_key[key] = source_hash
        elif existing_hash and source_hash and existing_hash != source_hash:
            source_hash_by_key[key] = ""

    return source_hash_by_key, source_variants_by_key


def _select_docs_by_keys(docs: list[Any], keys: set[str]) -> list[Any]:
    selected: list[Any] = []
    for doc in docs:
        key = _doc_source_key(doc)
        if key and key in keys:
            selected.append(doc)
    return selected


def _attach_source_hash(chunks: list[Any], source_hash_by_key: dict[str, str]) -> None:
    for chunk in chunks:
        metadata = getattr(chunk, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}

        source = _extract_source(metadata)
        if not source:
            chunk.metadata = metadata
            continue

        key = _source_key(source)
        source_hash = source_hash_by_key.get(key, "")
        if source_hash:
            metadata["source_hash"] = source_hash

        chunk.metadata = metadata


def _delete_chunks_by_sources(db: Chroma, sources: set[str]) -> int:
    deleted_chunks = 0

    for source in sorted(sources):
        rows = db.get(where={"source": source}, include=["metadatas"])
        ids = rows.get("ids", [])
        if not ids:
            continue
        db.delete(ids=ids)
        deleted_chunks += len(ids)

    return deleted_chunks


def _batched(items: list[Any], batch_size: int) -> list[list[Any]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def _add_chunks_in_batches(
    db: Chroma,
    chunks: list[Any],
    batch_size: int = 64,
    progress_callback: ProgressCallback | None = None,
) -> None:
    if not chunks:
        message = "No chunks to embed/write."
        print(message)
        if progress_callback:
            progress_callback(message, 1.0)
        return

    batches = _batched(chunks, batch_size)
    total_batches = len(batches)
    message = (
        f"Writing {len(chunks)} chunks in {total_batches} batches (batch_size={batch_size})..."
    )
    print(message)
    if progress_callback:
        progress_callback(message, 0.2)

    for index, batch in enumerate(batches, start=1):
        progress = 0.2 + (index / total_batches) * 0.75
        batch_message = f"Batch {index}/{total_batches}: {len(batch)} chunks"
        print(f"  {batch_message}")
        if progress_callback:
            progress_callback(batch_message, min(progress, 0.95))
        db.add_documents(batch)


def _new_stats(mode_text: str, docs_total: int, persist_dir: Path) -> dict[str, int | str]:
    return {
        "mode": mode_text,
        "docs_total": docs_total,
        "docs_indexed": 0,
        "skipped_docs": 0,
        "added_docs": 0,
        "updated_docs": 0,
        "deleted_docs": 0,
        "unchanged_docs": 0,
        "chunks": 0,
        "chunks_written": 0,
        "deleted_chunks": 0,
        "persist_dir": str(persist_dir),
    }


def _build_splitter(settings: Any) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def _split_markdown_sections(doc: Document) -> list[Document]:
    text = doc.page_content
    lines = text.splitlines()

    metadata_lines: list[str] = []
    content_start = 0
    if lines and lines[0].strip() == "# Source Metadata":
        metadata_lines.append(lines[0])
        for index in range(1, len(lines)):
            metadata_lines.append(lines[index])
            if not lines[index].strip():
                content_start = index + 1
                break

    body_lines = lines[content_start:]
    sections: list[tuple[str | None, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in body_lines:
        heading_match = SECTION_HEADING_RE.match(line)
        if heading_match:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line.strip()
            current_lines = [line]
            continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    if not sections:
        return [doc]

    section_docs: list[Document] = []
    for index, (section_title, section_lines) in enumerate(sections):
        content = "\n".join(section_lines).strip()
        if not content:
            continue
        merged = content
        if metadata_lines:
            merged = "\n".join(metadata_lines).rstrip() + "\n\n" + content
        metadata = dict(doc.metadata)
        metadata["chunk_strategy"] = "section"
        if section_title:
            metadata["section_title"] = section_title.lstrip("# ").strip()
            metadata["section_heading"] = section_title
        metadata["section_index"] = index
        section_docs.append(Document(page_content=merged, metadata=metadata))

    return section_docs or [doc]


def _split_docs(
    docs: list[Document],
    strategy: str,
    splitter: RecursiveCharacterTextSplitter,
) -> list[Document]:
    if strategy == "fixed":
        chunks = splitter.split_documents(docs)
        for chunk in chunks:
            if isinstance(chunk.metadata, dict):
                chunk.metadata["chunk_strategy"] = "fixed"
        return chunks

    if strategy == "section":
        chunks: list[Document] = []
        for doc in docs:
            chunks.extend(_split_markdown_sections(doc))
        return chunks

    if strategy == "hybrid":
        section_docs: list[Document] = []
        for doc in docs:
            section_docs.extend(_split_markdown_sections(doc))
        chunks = splitter.split_documents(section_docs)
        for chunk in chunks:
            if isinstance(chunk.metadata, dict):
                chunk.metadata["chunk_strategy"] = "hybrid"
        return chunks

    raise ValueError(f"Unsupported chunk strategy: {strategy}")


def build_index(
    mode: str = "rebuild",
    chunk_strategy: str = "fixed",
    progress_callback: ProgressCallback | None = None,
) -> dict[str, int | str]:
    if mode not in {"rebuild", "append", "sync"}:
        raise ValueError(f"Unsupported mode: {mode}")
    if chunk_strategy not in {"fixed", "section", "hybrid"}:
        raise ValueError(f"Unsupported chunk strategy: {chunk_strategy}")

    settings = load_settings()

    data_path = Path(settings.data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    text_loader_kwargs = {"encoding": "utf-8"}

    txt_loader = DirectoryLoader(
        str(data_path),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs=text_loader_kwargs,
        show_progress=True,
    )
    md_loader = DirectoryLoader(
        str(data_path),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs=text_loader_kwargs,
        show_progress=True,
    )

    docs = txt_loader.load() + md_loader.load()
    if not docs:
        raise ValueError(f"No .txt or .md files found under {data_path}")

    splitter = _build_splitter(settings)

    embedding_kwargs = {
        "model": settings.embedding_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        embedding_kwargs["base_url"] = settings.openai_base_url

    embeddings = OpenAIEmbeddings(**embedding_kwargs)

    chroma_dir = Path(settings.chroma_dir)
    if mode == "rebuild" and chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    source_hash_by_key = _build_current_source_hashes(docs)
    stats = _new_stats(f"{mode}:{chunk_strategy}", len(docs), chroma_dir)

    message = f"Preparing to index {len(docs)} documents with chunk_strategy={chunk_strategy}..."
    print(message)
    if progress_callback:
        progress_callback(message, 0.05)

    if mode == "rebuild":
        docs_to_index = docs
        chunks = _split_docs(docs_to_index, chunk_strategy, splitter)
        _attach_source_hash(chunks, source_hash_by_key)
        message = f"Split into {len(chunks)} chunks, now computing embeddings..."
        print(message)
        if progress_callback:
            progress_callback(message, 0.15)

        db = Chroma(
            persist_directory=str(chroma_dir),
            embedding_function=embeddings,
        )
        _add_chunks_in_batches(db, chunks, progress_callback=progress_callback)

        message = "Embedding complete, persisting..."
        print(message)
        if progress_callback:
            progress_callback(message, 0.98)

        stats["docs_indexed"] = len(docs_to_index)
        stats["added_docs"] = len(docs_to_index)
        stats["chunks"] = len(chunks)
        stats["chunks_written"] = len(chunks)
    else:
        message = f"Loading existing Chroma database from {chroma_dir}..."
        print(message)
        if progress_callback:
            progress_callback(message, 0.05)
        db = Chroma(
            persist_directory=str(chroma_dir),
            embedding_function=embeddings,
        )
        message = "Chroma database loaded."
        print(message)
        if progress_callback:
            progress_callback(message, 0.12)

        existing_hash_by_key, existing_sources_by_key = _load_existing_state(db)
        existing_keys = set(existing_hash_by_key)
        current_keys = set(source_hash_by_key)

        if mode == "append":
            added_keys = current_keys - existing_keys
            unchanged_keys = current_keys & existing_keys
            docs_to_index = _select_docs_by_keys(docs, added_keys)
            chunks = _split_docs(docs_to_index, chunk_strategy, splitter) if docs_to_index else []
            _attach_source_hash(chunks, source_hash_by_key)
            if chunks:
                message = f"Append mode will write {len(chunks)} chunks."
                print(message)
                if progress_callback:
                    progress_callback(message, 0.18)
                _add_chunks_in_batches(db, chunks, progress_callback=progress_callback)

            stats["docs_indexed"] = len(docs_to_index)
            stats["skipped_docs"] = len(docs) - len(docs_to_index)
            stats["added_docs"] = len(added_keys)
            stats["unchanged_docs"] = len(unchanged_keys)
            stats["chunks"] = len(chunks)
            stats["chunks_written"] = len(chunks)
        else:
            added_keys = current_keys - existing_keys
            deleted_keys = existing_keys - current_keys
            overlap_keys = current_keys & existing_keys
            updated_keys = {
                key
                for key in overlap_keys
                if not existing_hash_by_key.get(key)
                or existing_hash_by_key.get(key) != source_hash_by_key.get(key)
            }
            unchanged_keys = overlap_keys - updated_keys

            sources_to_delete: set[str] = set()
            for key in deleted_keys | updated_keys:
                sources_to_delete.update(existing_sources_by_key.get(key, set()))
            deleted_chunks = _delete_chunks_by_sources(db, sources_to_delete)

            keys_to_index = added_keys | updated_keys
            docs_to_index = _select_docs_by_keys(docs, keys_to_index)
            chunks = _split_docs(docs_to_index, chunk_strategy, splitter) if docs_to_index else []
            _attach_source_hash(chunks, source_hash_by_key)
            if chunks:
                message = (
                    f"Sync mode will write {len(chunks)} chunks after deleting {deleted_chunks} old chunks."
                )
                print(message)
                if progress_callback:
                    progress_callback(message, 0.18)
                _add_chunks_in_batches(db, chunks, progress_callback=progress_callback)

            stats["docs_indexed"] = len(docs_to_index)
            stats["skipped_docs"] = len(docs) - len(docs_to_index)
            stats["added_docs"] = len(added_keys)
            stats["updated_docs"] = len(updated_keys)
            stats["deleted_docs"] = len(deleted_keys)
            stats["unchanged_docs"] = len(unchanged_keys)
            stats["chunks"] = len(chunks)
            stats["chunks_written"] = len(chunks)
            stats["deleted_chunks"] = deleted_chunks

    print(
        f"Indexed {stats['docs_indexed']}/{stats['docs_total']} documents into {stats['chunks_written']} chunks. "
        f"mode={stats['mode']} skipped_docs={stats['skipped_docs']} "
        f"added={stats['added_docs']} updated={stats['updated_docs']} deleted={stats['deleted_docs']} "
        f"unchanged={stats['unchanged_docs']}"
    )
    print(f"Persisted vector DB to: {stats['persist_dir']}")

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build or update Chroma index")
    parser.add_argument(
        "--mode",
        choices=["rebuild", "append", "sync"],
        default="rebuild",
        help="rebuild: recreate vector DB; append: add only new sources; sync: add/update/delete to match source files",
    )
    parser.add_argument(
        "--chunk-strategy",
        choices=["fixed", "section", "hybrid"],
        default="fixed",
        help="fixed: existing fixed-size chunking; section: split by markdown headings; hybrid: split by headings then re-split long sections",
    )
    args = parser.parse_args()

    build_index(mode=args.mode, chunk_strategy=args.chunk_strategy)
