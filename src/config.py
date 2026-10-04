"""Application settings loaded from environment variables and an optional `.env` file."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["gemini", "openai"]
SearchType = Literal["similarity", "mmr"]

PROVIDER_LABELS: dict[str, str] = {"gemini": "Google Gemini", "openai": "OpenAI"}

# Chat models offered in the sidebar dropdown (first entry is the default).
CHAT_MODELS: dict[str, list[str]] = {
    "gemini": ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.1-pro-preview"],
    "openai": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-5-mini"],
}


class Settings(BaseSettings):
    """Typed application configuration. Every field can be overridden by an env var of the same name."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_api_key: str = ""
    openai_api_key: str = ""

    default_provider: Provider = "gemini"
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    chunk_size: int = Field(default=1000, ge=200, le=4000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)
    top_k: int = Field(default=4, ge=1, le=20)
    search_type: SearchType = "similarity"

    max_file_size_mb: int = Field(default=20, ge=1)
    url_timeout_seconds: int = Field(default=15, ge=1)
    max_history_turns: int = Field(default=6, ge=0)
    vectorstore_dir: str = "vectorstore"
    # Off by default: a saved index on a shared server would be reloaded for every visitor.
    # Turn on only for a private, single-user install.
    persist_index: bool = False
    log_level: str = "INFO"

    def chat_model_for(self, provider: str) -> str:
        """Return the configured default chat model for a provider."""
        return self.gemini_chat_model if provider == "gemini" else self.openai_chat_model

    def embedding_model_for(self, provider: str) -> str:
        """Return the configured embedding model for a provider."""
        return self.gemini_embedding_model if provider == "gemini" else self.openai_embedding_model

    def api_key_for(self, provider: str) -> str:
        """Return the API key from the environment for a provider (may be empty)."""
        return self.google_api_key if provider == "gemini" else self.openai_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging once with a compact, readable format."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Third-party libraries are chatty at INFO level.
    for noisy in ("faiss", "httpx", "urllib3", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
