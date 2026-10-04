from langchain_core.messages import HumanMessage

from src.config import CHAT_MODELS, PROVIDER_LABELS, Settings
from src.llm import MissingAPIKeyError, get_chat_model, resolve_api_key

import pytest


def test_every_provider_is_fully_configured():
    settings = Settings(_env_file=None, anthropic_api_key="sk-ant-env")
    for provider in PROVIDER_LABELS:
        assert CHAT_MODELS[provider]
        assert settings.chat_model_for(provider)
        assert settings.embedding_model_for(provider)
    assert settings.api_key_for("anthropic") == "sk-ant-env"
    assert settings.embedding_model_for("anthropic") == settings.local_embedding_model


def test_anthropic_key_from_streamlit_secrets():
    assert resolve_api_key("anthropic", secrets={"ANTHROPIC_API_KEY": "sk-ant-s"}) == "sk-ant-s"


def test_claude_requires_key():
    with pytest.raises(MissingAPIKeyError):
        get_chat_model("anthropic", "claude-opus-5-5", "")


def _payload(model):
    llm = get_chat_model("anthropic", model, "sk-ant-test", temperature=0.3)
    return llm._get_request_payload([HumanMessage("hi")])


def test_opus_has_fallbacks_and_no_sampling_params():
    payload = _payload("claude-opus-5-5")
    assert payload["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in payload["betas"]
    assert "temperature" not in payload and "temperature" not in payload.get("extra_body", {})


def test_sonnet_sends_no_temperature():
    payload = _payload("claude-sonnet-5-5")
    assert "temperature" not in payload and "temperature" not in payload.get("extra_body", {})
