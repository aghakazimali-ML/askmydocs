"""Tests for the Studio tools using fake models (no API key, no network)."""

from __future__ import annotations

import json

import pytest
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.chain import build_rag_chain, build_retriever, ask
from src.studio import (
    StudioError,
    chunks_for,
    extract_json,
    library_stats,
    mindmap_to_dot,
    parse_flashcards,
    parse_mindmap,
    parse_quiz,
    run_tool,
    sample_context,
    top_keywords,
)
from src.vectorstore import add_chunks, stored_chunks

CHUNKS = [
    Document(page_content="The project budget is 50000 dollars.", metadata={"source": "plan.pdf", "page": 1, "chunk_id": "p1"}),
    Document(page_content="The launch date is March 3rd.", metadata={"source": "plan.pdf", "page": 2, "chunk_id": "p2"}),
    Document(page_content="The team has five engineers working remotely.", metadata={"source": "team.pdf", "page": 4, "chunk_id": "t4"}),
]

QUIZ_JSON = json.dumps([
    {"question": "What is the budget?", "options": ["10k", "50k", "90k", "1M"], "answer_index": 1,
     "explanation": "plan.pdf p.1", "source": "plan.pdf"},
    {"question": "Broken", "options": ["a"], "answer_index": 3},
])


def test_extract_json_handles_fences_and_chatter() -> None:
    assert extract_json('Sure!\n```json\n[{"a": 1}]\n```') == [{"a": 1}]
    assert extract_json('{"title": "x", "branches": []}') == {"title": "x", "branches": []}
    with pytest.raises(StudioError):
        extract_json("no json here")


def test_parse_quiz_drops_invalid_items() -> None:
    quiz = parse_quiz(QUIZ_JSON)
    assert len(quiz) == 1 and quiz[0]["answer_index"] == 1
    with pytest.raises(StudioError):
        parse_quiz("[]")


def test_parse_flashcards_and_mindmap() -> None:
    cards = parse_flashcards('{"cards": [{"front": "Budget?", "back": "50k"}, {"front": "x"}]}')
    assert cards == [{"front": "Budget?", "back": "50k"}]
    mm = parse_mindmap('{"title": "Plan \\"A\\"", "branches": [{"name": "Money", "children": ["50k"]}]}')
    dot = mindmap_to_dot(mm)
    assert dot.startswith("digraph") and '\\"A\\"' in dot and "b0c0" in dot


def test_run_tool_markdown_quiz_and_compare_rules() -> None:
    summary = run_tool(FakeListChatModel(responses=["### TL;DR\nA plan."]), "summary", CHUNKS)
    assert summary["markdown"].startswith("### TL;DR") and summary["documents"] == ["plan.pdf", "team.pdf"]

    quiz = run_tool(FakeListChatModel(responses=[QUIZ_JSON]), "quiz", CHUNKS, {"count": 2})
    assert len(quiz["data"]) == 1 and "✅ 50k" in quiz["markdown"]

    with pytest.raises(StudioError):
        run_tool(FakeListChatModel(responses=["x"]), "compare", chunks_for(CHUNKS, ["plan.pdf"]))
    with pytest.raises(StudioError):
        run_tool(FakeListChatModel(responses=["x"]), "summary", [])


def test_context_sampling_and_filtering() -> None:
    assert [c.metadata["source"] for c in chunks_for(CHUNKS, ["team.pdf"])] == ["team.pdf"]
    assert chunks_for(CHUNKS, []) == CHUNKS
    many = [Document(page_content="x" * 100, metadata={"source": "a"}) for _ in range(100)]
    assert 1 <= len(sample_context(many, max_chars=1000)) <= 10


def test_library_stats_and_keywords() -> None:
    rows = {r["Document"]: r for r in library_stats(CHUNKS)}
    assert rows["plan.pdf"]["Pages"] == 2 and rows["plan.pdf"]["Chunks"] == 2
    words = dict(top_keywords(CHUNKS))
    assert "budget" in words and "the" not in words


def test_stored_chunks_reads_back_faiss_index() -> None:
    store = add_chunks(None, CHUNKS, FakeEmbeddings(size=16))
    assert [c.page_content for c in stored_chunks(store)] == [c.page_content for c in CHUNKS]
    assert stored_chunks(None) == []


def test_rag_chain_accepts_style_and_language() -> None:
    store = add_chunks(None, CHUNKS, FakeEmbeddings(size=16))
    chain = build_rag_chain(FakeListChatModel(responses=["ok"]), build_retriever(store, k=1), "Executive", "Urdu")
    assert ask(chain, "Budget?")["answer"] == "ok"
