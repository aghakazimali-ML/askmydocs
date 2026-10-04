"""FAISS vector store helpers: build, extend, save/load to disk, and content hashing for de-duplication."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
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


def add_chunks(store: FAISS | None, chunks: list[Document], embeddings: Embeddings) -> FAISS:
    """Embed chunks and add them to `store`, creating a new FAISS index if `store` is None."""
    if not chunks:
        if store is None:
            raise ValueError("Cannot build an index from zero chunks.")
        return store
    ids = [str(c.metadata.get("chunk_id")) for c in chunks]
    if store is None:
        logger.info("Building new FAISS index with %d chunks", len(chunks))
        return FAISS.from_documents(chunks, embeddings, ids=ids)
    logger.info("Adding %d chunks to existing FAISS index", len(chunks))
    store.add_documents(chunks, ids=ids)
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
