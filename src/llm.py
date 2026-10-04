"""Factories for chat models and embeddings (Google Gemini, OpenAI or Anthropic Claude), plus API-key helpers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.config import PROVIDER_LABELS

logger = logging.getLogger(__name__)

_SECRET_NAMES = {"gemini": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}

# Opus 5.5 can hand an overloaded request to another Claude model on Anthropic's side instead of failing.
_SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"


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
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {"model": model, "api_key": api_key, "max_retries": 2, "max_tokens": 16000, "streaming": True}
        # Opus 5.5 and Sonnet 5.5 reject non-default sampling parameters; Haiku 4.5 accepts temperature.
        if model.startswith("claude-haiku"):
            kwargs["temperature"] = temperature
        if model == "claude-opus-5-5":
            kwargs["betas"] = [_SERVER_FALLBACK_BETA]
            kwargs["model_kwargs"] = {"fallbacks": "default"}
        return ChatAnthropic(**kwargs)
    raise ValueError(f"Unknown provider: {provider}")


def get_embeddings(provider: str, model: str, api_key: str) -> Embeddings:
    """Create the embeddings client matching the chat provider."""
    logger.info("Creating embeddings %s/%s", provider, model)
    if provider == "anthropic":
        # Runs on this machine: no API key, no cost, no rate limit. The model downloads once (~130 MB).
        from langchain_community.embeddings import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=model)
    _require_key(provider, api_key)
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
    if any(s in text for s in ("api key not valid", "api_key_invalid", "x-api-key", "incorrect api key", "invalid_api_key",
                               "authentication", "unauthorized", "401", "permission_denied")):
        return "Your API key was rejected. Please check that it is correct and belongs to the selected provider."
    if any(s in text for s in ("quota", "rate limit", "ratelimit", "resource_exhausted", "resourceexhausted", "429")):
        return "The provider's rate limit or quota was reached. Wait a minute and try again, or use another key."
    if any(s in text for s in ("not found", "404", "does not exist", "model_not_found")):
        return "The selected model is not available for your API key. Try another model in the sidebar."
    if any(s in text for s in ("timeout", "timed out", "connection", "network")):
        return "Could not reach the AI provider. Check your internet connection and try again."
    return "Something went wrong while talking to the AI provider. Please try again."
