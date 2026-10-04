"""Tests for the RAG chain using fake models (no API key, no network)."""

from __future__ import annotations

from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from src.chain import (
    StreamedAnswer,
    ask,
    build_rag_chain,
    build_retriever,
    docs_to_sources,
    format_source_label,
    to_chat_history,
)
from src.export import chat_to_markdown
from src.suggestions import generate_suggested_questions, parse_questions
from src.vectorstore import add_chunks, content_hash, load_vectorstore, read_manifest, save_vectorstore

CHUNKS = [
    Document(page_content="The project budget is 50000 dollars.", metadata={"source": "plan.pdf", "page": 1, "chunk_id": "plan.pdf::p1::c1"}),
    Document(page_content="The launch date is March 3rd.", metadata={"source": "plan.pdf", "page": 2, "chunk_id": "plan.pdf::p2::c1"}),
    Document(page_content="The team has five engineers.", metadata={"source": "team.pdf", "page": 4, "chunk_id": "team.pdf::p4::c1"}),
]


def _store():
    return add_chunks(None, CHUNKS, FakeEmbeddings(size=32))


def test_chain_returns_answer_and_sources() -> None:
    llm = FakeListChatModel(responses=["The budget is 50000 dollars (plan.pdf, p. 1)."])
    chain = build_rag_chain(llm, build_retriever(_store(), k=2))
    result = ask(chain, "What is the budget?")
    assert result["answer"].startswith("The budget is")
    assert len(result["context"]) == 2
    assert all(isinstance(d, Document) for d in result["context"])
    sources = docs_to_sources(result["context"])
    assert {"source", "page", "preview", "chunk_id"} <= set(sources[0])


def test_follow_up_uses_history_rewrite() -> None:
    # First response is consumed by the question-rewriting step, second is the final answer.
    llm = FakeListChatModel(responses=["When is the launch date?", "It launches on March 3rd (plan.pdf, p. 2)."])
    chain = build_rag_chain(llm, build_retriever(_store(), k=3, search_type="mmr"))
    history = [HumanMessage(content="Tell me about the launch"), AIMessage(content="There is a launch planned.")]
    result = ask(chain, "When is it?", history)
    assert result["answer"] == "It launches on March 3rd (plan.pdf, p. 2)."
    assert result["context"]


def test_streaming_yields_tokens_and_captures_context() -> None:
    llm = FakeListChatModel(responses=["Five engineers."])
    chain = build_rag_chain(llm, build_retriever(_store(), k=1))
    stream = StreamedAnswer(chain, "How big is the team?", [])
    tokens = list(stream)
    assert len(tokens) > 1, "answer should arrive in several chunks"
    assert "".join(tokens) == stream.answer == "Five engineers."
    assert len(stream.context) == 1


def test_save_and_load_roundtrip(tmp_path) -> None:
    store = _store()
    save_vectorstore(store, tmp_path, {"provider": "gemini", "embedding_model": "fake", "documents": ["plan.pdf"]})
    assert read_manifest(tmp_path)["documents"] == ["plan.pdf"]
    loaded = load_vectorstore(tmp_path, FakeEmbeddings(size=32))
    assert loaded.index.ntotal == len(CHUNKS)


def test_helpers() -> None:
    assert content_hash(b"abc") == content_hash("abc")
    assert format_source_label("a.pdf", 4) == "📄 a.pdf — page 4"
    assert format_source_label("https://x.com", None) == "🌐 https://x.com"
    msgs = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    assert [type(m) for m in to_chat_history(msgs)] == [HumanMessage, AIMessage]


def test_suggestions_and_export() -> None:
    llm = FakeListChatModel(responses=['["What is the budget?", "When is launch?", "Who is on the team?"]'])
    assert generate_suggested_questions(llm, CHUNKS) == ["What is the budget?", "When is launch?", "Who is on the team?"]
    assert parse_questions("1. What is X?\n2. Why Y?") == ["What is X?", "Why Y?"]
    md = chat_to_markdown(
        [
            {"role": "user", "content": "Budget?"},
            {"role": "assistant", "content": "50000.", "sources": docs_to_sources(CHUNKS[:1])},
        ],
        ["plan.pdf"],
    )
    assert "📄 plan.pdf — page 1" in md and "## Conversation" in md
