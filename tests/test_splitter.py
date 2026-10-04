"""Tests for chunking: size/overlap limits and metadata preservation."""

from __future__ import annotations

import pytest
from langchain_core.documents import Document

from src.splitter import split_documents


@pytest.fixture()
def long_docs() -> list[Document]:
    sentence = "Retrieval augmented generation grounds answers in documents. "
    return [
        Document(page_content=sentence * 60, metadata={"source": "a.pdf", "page": 1}),
        Document(page_content=sentence * 40, metadata={"source": "a.pdf", "page": 2}),
        Document(page_content=sentence * 30, metadata={"source": "https://x.com", "page": None}),
    ]


def test_chunks_respect_size(long_docs: list[Document]) -> None:
    chunks = split_documents(long_docs, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > len(long_docs)
    assert all(len(c.page_content) <= 300 for c in chunks)


def test_chunks_overlap(long_docs: list[Document]) -> None:
    chunks = split_documents(long_docs[:1], chunk_size=300, chunk_overlap=80)
    first, second = chunks[0], chunks[1]
    # The next chunk starts before the previous one ends → shared text.
    assert second.metadata["start_index"] < first.metadata["start_index"] + len(first.page_content)
    tail = first.page_content[-40:].strip()
    assert tail in second.page_content


def test_metadata_preserved_on_every_chunk(long_docs: list[Document]) -> None:
    chunks = split_documents(long_docs, chunk_size=300, chunk_overlap=50)
    for chunk in chunks:
        assert "source" in chunk.metadata
        assert "page" in chunk.metadata
        assert chunk.metadata["chunk_id"]
    assert {c.metadata["page"] for c in chunks if c.metadata["source"] == "a.pdf"} == {1, 2}
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), "chunk_id must be unique"


def test_invalid_overlap_rejected(long_docs: list[Document]) -> None:
    with pytest.raises(ValueError):
        split_documents(long_docs, chunk_size=100, chunk_overlap=100)
