from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str
    embedding_model: str
    chat_model: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    data_dir: str
    chroma_dir: str


def load_settings() -> Settings:
    load_dotenv(override=True)

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise ValueError("Missing OPENAI_API_KEY. Please set it in your .env file.")

    chunk_size = int(os.getenv("CHUNK_SIZE", "1200"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "150"))
    if chunk_overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")

    top_k = int(os.getenv("TOP_K", "4"))
    if top_k <= 0:
        raise ValueError("TOP_K must be greater than 0.")

    return Settings(
        openai_api_key=openai_api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        chat_model=os.getenv("CHAT_MODEL", "gpt-4o-mini"),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        data_dir=os.getenv("DATA_DIR", "data/protocols"),
        chroma_dir=os.getenv("CHROMA_DIR", "chroma_db"),
    )
