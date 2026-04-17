from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from src.config import load_settings


def get_retriever():
    settings = load_settings()

    chroma_dir = Path(settings.chroma_dir)
    if not chroma_dir.exists():
        raise FileNotFoundError(
            f"Vector DB not found at {chroma_dir}. Please run: python -m src.ingest"
        )

    embedding_kwargs = {
        "model": settings.embedding_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        embedding_kwargs["base_url"] = settings.openai_base_url

    embeddings = OpenAIEmbeddings(**embedding_kwargs)

    db = Chroma(
        persist_directory=str(chroma_dir),
        embedding_function=embeddings,
    )

    return db.as_retriever(search_kwargs={"k": settings.top_k})
