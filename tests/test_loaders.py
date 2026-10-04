"""Tests for PDF/URL loading and validation (offline)."""

from __future__ import annotations

import pytest

from src.loaders import (
    DocumentLoadError,
    EmptyDocumentError,
    FileTooLargeError,
    load_pdf_bytes,
    parse_urls,
)


def test_pdf_loads_with_one_based_pages(sample_pdf_bytes: bytes) -> None:
    docs = load_pdf_bytes(sample_pdf_bytes, "sample.pdf")
    assert [d.metadata["page"] for d in docs] == [1, 2]
    assert all(d.metadata["source"] == "sample.pdf" for d in docs)
    assert "budget" in docs[0].page_content
    assert "launch date" in docs[1].page_content


def test_oversized_file_raises(sample_pdf_bytes: bytes) -> None:
    big = sample_pdf_bytes + b"0" * (2 * 1024 * 1024)
    with pytest.raises(FileTooLargeError):
        load_pdf_bytes(big, "big.pdf", max_size_mb=1)


def test_zero_byte_file_raises() -> None:
    with pytest.raises(EmptyDocumentError):
        load_pdf_bytes(b"", "empty.pdf")


def test_pdf_without_text_raises(blank_pdf_bytes: bytes) -> None:
    with pytest.raises(EmptyDocumentError, match="no extractable text"):
        load_pdf_bytes(blank_pdf_bytes, "scanned.pdf")


def test_non_pdf_raises() -> None:
    with pytest.raises(DocumentLoadError):
        load_pdf_bytes(b"hello, I am a text file", "notes.pdf")


def test_custom_errors_share_base_class() -> None:
    assert issubclass(FileTooLargeError, DocumentLoadError)
    assert issubclass(EmptyDocumentError, DocumentLoadError)


def test_parse_urls_splits_valid_and_invalid() -> None:
    valid, invalid = parse_urls("https://a.com/x\n\nnot a url\nhttp://b.org\nhttps://a.com/x\n")
    assert valid == ["https://a.com/x", "http://b.org"]
    assert invalid == ["not a url"]


def test_bundled_samples_load_as_sections() -> None:
    from pathlib import Path

    from src.loaders import load_markdown_sections

    samples = sorted((Path(__file__).resolve().parents[1] / "docs" / "samples").glob("*.md"))
    assert len(samples) == 2
    docs = load_markdown_sections(samples[0])
    assert len(docs) >= 5
    assert docs[0].metadata == {"source": samples[0].name, "page": 1, "type": "sample"}
    assert all(d.page_content.strip() for d in docs)
