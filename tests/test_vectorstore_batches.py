"""Batched embedding with rate-limit retries."""

import pytest
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document

from src.vectorstore import add_chunks, stored_chunks


def _chunks(n: int, prefix: str = "c") -> list[Document]:
    return [Document(page_content=f"text {prefix}{i}", metadata={"chunk_id": f"{prefix}{i}"}) for i in range(n)]


class FlakyEmbeddings(FakeEmbeddings):
    """Raises a 429-style error on the first `fail_times` calls."""

    fail_times: int = 0
    calls: int = 0

    def embed_documents(self, texts):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")
        return super().embed_documents(texts)


def test_batches_and_retries_after_rate_limit():
    emb = FlakyEmbeddings(size=8, fail_times=2)
    waits, progress = [], []
    store = add_chunks(None, _chunks(25), emb, batch_size=10, waits=(1, 2, 3), sleep=waits.append,
                       on_progress=lambda d, t, w: progress.append((d, t, w)))
    assert len(stored_chunks(store)) == 25
    assert waits == [1, 2]
    assert progress[-1] == (25, 25, 0)


def test_gives_up_and_leaves_existing_store_untouched():
    store = add_chunks(None, _chunks(3, "old"), FakeEmbeddings(size=8))
    emb = FlakyEmbeddings(size=8, fail_times=99)
    with pytest.raises(RuntimeError, match="429"):
        add_chunks(store, _chunks(5, "new"), emb, batch_size=2, waits=(1,), sleep=lambda s: None)
    assert len(stored_chunks(store)) == 3


def test_other_errors_are_not_retried():
    class Broken(FakeEmbeddings):
        def embed_documents(self, texts):
            raise ValueError("API key not valid")

    slept = []
    with pytest.raises(ValueError):
        add_chunks(None, _chunks(3), Broken(size=8), waits=(1, 2), sleep=slept.append)
    assert slept == []
