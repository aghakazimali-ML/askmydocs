"""Factories for chat models and embeddings (Google Gemini or OpenAI), plus API-key helpers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.config import PROVIDER_LABELS

logger = logging.getLogger(__name__)

_SECRET_NAMES = {"gemini": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY"}


class MissingAPIKeyError(ValueError):
    """Raised when no API key is available for the selected provider."""


def resolve_api_key(provider: str, sidebar_key: str = "", env_key: str = "", secrets: Mapping[str, Any] | None = None) -> str:
    """Pick the API key in priority order: sidebar input → `.env`/environment → Streamlit secrets."""
    for candidate in (sidebar_key, env_key):
        if candidate and candidate.strip():
            return candidate.strip()
    if secrets:
        value = secrets.get(_SECRET_NAMES[provider], "")
        if value:
            return str(value).strip()
    return ""


def _require_key(provider: str, api_key: str) -> None:
    if not api_key:
        raise MissingAPIKeyError(
            f"No API key found for {PROVIDER_LABELS.get(provider, provider)}. "
            f"Paste it in the sidebar or set {_SECRET_NAMES[provider]} in your .env file."
        )


def _supports_temperature(model: str) -> bool:
    """OpenAI reasoning models (gpt-5*, o-series) only accept the default temperature."""
    name = model.lower()
    return not (name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3") or name.startswith("o4"))


def get_chat_model(provider: str, model: str, api_key: str, temperature: float = 0.1) -> BaseChatModel:
    """Create a streaming-capable chat model for the given provider."""
    _require_key(provider, api_key)
    logger.info("Creating chat model %s/%s", provider, model)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=temperature, max_retries=2)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {"model": model, "api_key": api_key, "max_retries": 2, "streaming": True}
        if _supports_temperature(model):
            kwargs["temperature"] = temperature
        return ChatOpenAI(**kwargs)
    raise ValueError(f"Unknown provider: {provider}")


def get_embeddings(provider: str, model: str, api_key: str) -> Embeddings:
    """Create the embeddings client matching the chat provider."""
    _require_key(provider, api_key)
    logger.info("Creating embeddings %s/%s", provider, model)
    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model, api_key=api_key)
    raise ValueError(f"Unknown provider: {provider}")


def describe_provider_error(exc: Exception) -> str:
    """Turn a provider/SDK exception into a short, user-friendly message (no stack trace)."""
    if isinstance(exc, MissingAPIKeyError):
        return str(exc)
    text = f"{type(exc).__name__}: {exc}".lower()
    if any(s in text for s in ("api key not valid", "api_key_invalid", "incorrect api key", "invalid_api_key",
                               "authentication", "unauthorized", "401", "permission_denied")):
        return "Your API key was rejected. Please check that it is correct and belongs to the selected provider."
    if any(s in text for s in ("quota", "rate limit", "ratelimit", "resource_exhausted", "429")):
        return "The provider's rate limit or quota was reached. Wait a minute and try again, or use another key."
    if any(s in text for s in ("not found", "404", "does not exist", "model_not_found")):
        return "The selected model is not available for your API key. Try another model in the sidebar."
    if any(s in text for s in ("timeout", "timed out", "connection", "network")):
        return "Could not reach the AI provider. Check your internet connection and try again."
    return "Something went wrong while talking to the AI provider. Please try again."
