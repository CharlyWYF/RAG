# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a local RAG app for answering questions about network protocols using a Streamlit UI, Chroma vector storage, and OpenAI-compatible embedding/chat models.

The repo has two main workflows:
- offline corpus preparation and indexing
- interactive QA through the Streamlit app

The current knowledge-base direction is RFC-centric. `docs/rfc_scope.md` and `docs/rfc_cleaning_rules.md` define the intended corpus boundaries and cleaning strategy; keep code changes aligned with those documents.

## Common Commands

### Environment setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If the project is being used with conda, the README’s existing flow is:

```bash
conda create -n rag-demo python=3.11 -y
conda activate rag-demo
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Configure local environment

```bash
cp .env.example .env
```

Required setting:
- `OPENAI_API_KEY`

Optional but supported:
- `OPENAI_BASE_URL` for OpenAI-compatible gateways
- `DATA_DIR`, `CHROMA_DIR`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `EMBEDDING_MODEL`, `CHAT_MODEL`

### Run the app

```bash
streamlit run app.py
```

### Build or update the vector index

Default rebuild flow:

```bash
python -m src.ingest
```

Useful variants:

```bash
python -m src.ingest --mode rebuild --chunk-strategy fixed
python -m src.ingest --mode rebuild --chunk-strategy section
python -m src.ingest --mode rebuild --chunk-strategy hybrid
python -m src.ingest --mode sync --chunk-strategy fixed
python -m src.ingest --mode append --chunk-strategy fixed
```

Mode semantics in `src/ingest.py`:
- `rebuild`: delete and recreate the whole Chroma directory
- `sync`: make the vector DB match current source files by add/update/delete
- `append`: only add new source files; does not handle modified or deleted sources

### Prepare corpus files

Download curated protocol sources:

```bash
python scripts/download_protocols.py
python scripts/download_protocols.py --kind spec
python scripts/download_protocols.py --protocol tcp,http,dns
```

Clean raw protocol/RFC documents into Markdown better suited for retrieval:

```bash
python scripts/clean_protocol_docs.py --raw-dir data/protocols --output-dir data/protocols/cleaned
```

Recommended follow-up after cleaning:
- point `DATA_DIR` at `data/protocols/cleaned`
- run `sync` or `rebuild`

## Validation

There is no dedicated automated test suite or linter configured in this repo today.

Useful manual validation steps:
- run `python -m src.ingest --mode rebuild --chunk-strategy hybrid` against a small local corpus
- run `streamlit run app.py`
- use the sidebar “测试 API 连通性” button to verify both chat and embedding connectivity
- ask a question after indexing and confirm retrieved contexts/sources are shown

## Architecture

### User-facing flow

`app.py` is the only app entrypoint. It renders three Streamlit tabs:
- `问答`: submits a question to the RAG pipeline and shows timings, logs, retrieved chunks, and sources
- `知识库管理`: uploads/deletes `.md`/`.txt` source files and triggers indexing
- `系统配置`: edits selected `.env` values from the UI and shows the currently effective settings

The sidebar is also important operationally: it exposes API health checks plus runtime progress/log/performance placeholders used by the QA and indexing flows.

### Configuration model

`src/config.py` is the single source of truth for runtime settings.
- `load_settings()` always reloads `.env` via `python-dotenv` with `override=True`
- it validates required values and basic numeric constraints
- many modules call `load_settings()` at execution time instead of sharing a long-lived global config

When changing configuration behavior, keep the UI editor in `app.py` and the runtime validation in `src/config.py` in sync.

### Retrieval and QA pipeline

The online question-answering path is split across:
- `src/retriever.py`: opens the persisted Chroma store and returns a retriever using `top_k`
- `src/qa.py`: orchestrates config loading, retriever creation, retrieval, prompt assembly, LLM invocation, and timing collection
- `app.py`: supplies progress callbacks and displays outputs

`src/qa.py` uses a strict prompt telling the model to answer only from retrieved context and to say “资料不足以确定” when evidence is insufficient. If you change answer style or citation behavior, update the prompt here first.

`health_check()` in `src/qa.py` validates both chat and embedding clients, so failures may come from model names, API key issues, or incompatible `OPENAI_BASE_URL` behavior.

### Indexing pipeline

`src/ingest.py` owns the offline indexing logic.

Important design points:
- source files are loaded from `DATA_DIR` using LangChain `DirectoryLoader` for both `.txt` and `.md`
- each source document gets a normalized source key and a content hash
- `sync` and `append` compare current documents against stored Chroma metadata instead of blindly rebuilding
- chunk metadata is enriched with `source_hash` and `chunk_strategy`
- section-aware chunking relies on Markdown headings; cleaned RFC files intentionally preserve/promote section structure for this reason

Chunking strategies:
- `fixed`: plain recursive character splitting
- `section`: split by Markdown headings only
- `hybrid`: split by Markdown headings, then re-split oversized sections with the recursive splitter

If retrieval quality changes unexpectedly, inspect the interaction between `scripts/clean_protocol_docs.py`, heading promotion, and the selected `chunk_strategy` before changing embedding or prompt logic.

### Corpus preparation pipeline

`scripts/clean_protocol_docs.py` is not just a helper; it encodes assumptions the indexing code depends on.

It:
- removes RFC noise such as page headers/footers, TOCs, and trailing references/author sections
- preserves or promotes structural headings into Markdown
- prepends a `# Source Metadata` block that becomes part of the indexed text
- writes cleaned output under `data/protocols/cleaned`

Because `src.ingest._split_markdown_sections()` explicitly looks for the `# Source Metadata` preamble and Markdown headings, preserve that contract when editing the cleaner.

`scripts/download_protocols.py` maintains a curated list of downloadable protocol materials. It currently includes tutorial and spec sources, but the project docs indicate the intended production corpus should remain RFC-first.

## Data and Persistence

Important directories:
- `data/protocols/`: source corpus location
- `data/protocols/cleaned/`: cleaned Markdown corpus used for structure-aware chunking
- `chroma_db/`: persisted vector store
- `docs/`: project constraints for corpus scope and cleaning rules

`chroma_db/chroma.sqlite3` is the quick readiness signal used by the UI.

## Change Guidance

When modifying this repo, pay attention to these couplings:
- changes to `.env` keys usually require updates in both `app.py` and `src/config.py`
- changes to chunking behavior often require corresponding updates in the cleaning script and possibly in README/docs examples
- changes to corpus scope should stay consistent with `docs/rfc_scope.md`
- changes to cleaning heuristics should stay consistent with `docs/rfc_cleaning_rules.md`

Keep implementations simple and local: this codebase is a small single-app project, and most behavior is intentionally centralized in a few files.
