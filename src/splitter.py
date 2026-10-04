"""Chunking logic: split loaded documents into overlapping, metadata-rich chunks."""

from __future__ import annotations

import logging
from collections import defaultdict

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def get_text_splitter(chunk_size: int = 1000, chunk_overlap: int = 150) -> RecursiveCharacterTextSplitter:
    """Build a RecursiveCharacterTextSplitter after validating the size/overlap combination."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size.")
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )


def split_documents(documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 150) -> list[Document]:
    """Split documents into chunks, keeping `source`/`page` and adding a unique `chunk_id` to each."""
    splitter = get_text_splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_documents(documents)

    counters: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        source = str(chunk.metadata.get("source", "unknown"))
        counters[source] += 1
        page = chunk.metadata.get("page")
        page_part = f"p{page}" if page is not None else "web"
        chunk.metadata["chunk_id"] = f"{source}::{page_part}::c{counters[source]}"

    logger.info("Split %d documents into %d chunks (size=%d, overlap=%d)", len(documents), len(chunks), chunk_size, chunk_overlap)
    return chunks
