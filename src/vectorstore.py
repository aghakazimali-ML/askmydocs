"""FAISS vector store helpers: build, extend, save/load to disk, and content hashing for de-duplication."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

MANIFEST_FILE = "manifest.json"


def content_hash(data: bytes | str) -> str:
    """Return the SHA-256 hex digest of file bytes (or a string such as a URL)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def embedding_signature(provider: str, model: str) -> str:
    """Identify which embedding model built an index (vectors from different models are incompatible)."""
    return f"{provider}:{model}"


EMBED_BATCH_SIZE = 40
RATE_LIMIT_WAITS = (10, 20, 40, 60, 60)  # seconds; free Gemini keys allow only a few embedding requests per minute


def is_rate_limit_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(s in text for s in ("quota", "rate limit", "ratelimit", "resource_exhausted", "resourceexhausted", "429"))


def add_chunks(
    store: FAISS | None,
    chunks: list[Document],
    embeddings: Embeddings,
    *,
    batch_size: int = EMBED_BATCH_SIZE,
    waits: tuple[float, ...] = RATE_LIMIT_WAITS,
    on_progress: Callable[[int, int, float], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> FAISS:
    """Embed chunks in small batches and add them to `store` (a new index if None).

    Batches that hit a provider rate limit are retried after a growing pause, so large PDFs
    still go through on free-tier keys. The file is only merged into `store` once every batch
    succeeds, so a failure never leaves a half-indexed document behind.
    on_progress(done, total, wait_seconds) is called after each batch and before each pause.
    """
    if not chunks:
        if store is None:
            raise ValueError("Cannot build an index from zero chunks.")
        return store
    logger.info("Embedding %d chunks in batches of %d", len(chunks), batch_size)
    staged: FAISS | None = None
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        ids = [str(c.metadata.get("chunk_id")) for c in batch]
        for attempt in range(len(waits) + 1):
            try:
                if staged is None:
                    staged = FAISS.from_documents(batch, embeddings, ids=ids)
                else:
                    staged.add_documents(batch, ids=ids)
                break
            except Exception as exc:
                if not is_rate_limit_error(exc) or attempt == len(waits):
                    raise
                wait = waits[attempt]
                logger.warning("Rate limited after %d/%d chunks; retrying in %ss", start, len(chunks), wait)
                if on_progress:
                    on_progress(start, len(chunks), wait)
                sleep(wait)
        if on_progress:
            on_progress(min(start + batch_size, len(chunks)), len(chunks), 0)
    if store is None:
        return staged
    store.merge_from(staged)
    return store


def save_vectorstore(store: FAISS, directory: str | Path, manifest: dict[str, Any]) -> None:
    """Persist the FAISS index plus a JSON manifest (indexed documents, hashes, embedding signature)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store.save_local(str(directory))
    (directory / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Saved vector store to %s", directory)


def read_manifest(directory: str | Path) -> dict[str, Any] | None:
    """Return the saved manifest, or None if no saved index exists."""
    directory = Path(directory)
    path = directory / MANIFEST_FILE
    if not (path.exists() and (directory / "index.faiss").exists()):
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Ignoring unreadable manifest at %s: %s", path, exc)
        return None


def load_vectorstore(directory: str | Path, embeddings: Embeddings) -> FAISS:
    """Load a FAISS index saved by `save_vectorstore`.

    `allow_dangerous_deserialization` is required because the docstore is pickled. It is safe here
    because the app only ever loads an index that it wrote itself into its own folder.
    """
    return FAISS.load_local(str(directory), embeddings, allow_dangerous_deserialization=True)


def delete_vectorstore(directory: str | Path) -> None:
    """Remove a saved index from disk (no-op if it does not exist)."""
    shutil.rmtree(Path(directory), ignore_errors=True)
    logger.info("Deleted saved vector store at %s", directory)


def stored_chunks(store: FAISS | None) -> list[Document]:
    """All chunks held in a FAISS index, in insertion order (works for freshly built and reloaded indexes)."""
    if store is None:
        return []
    ids = list(getattr(store, "index_to_docstore_id", {}).values())
    docs = getattr(store.docstore, "_dict", {})
    return [docs[i] for i in ids if i in docs]
