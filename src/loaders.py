"""Load PDFs and web pages into LangChain `Document`s with clean, consistent metadata."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

from langchain_core.documents import Document

# WebBaseLoader warns when no user agent is configured; set a polite default before importing it.
os.environ.setdefault("USER_AGENT", "AskMyDocs/1.0 (+https://github.com/aghakazimali-ML/askmydocs)")

from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader  # noqa: E402

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


class DocumentLoadError(Exception):
    """Base class for all user-facing ingestion errors."""


class FileTooLargeError(DocumentLoadError):
    """Raised when an uploaded file exceeds the size limit."""


class EmptyDocumentError(DocumentLoadError):
    """Raised when a file contains no extractable text (e.g. a scanned PDF)."""


class URLLoadError(DocumentLoadError):
    """Raised when a web page cannot be fetched or has no readable text."""


def validate_pdf_bytes(data: bytes, filename: str, max_size_mb: int = 20) -> None:
    """Check size and basic PDF signature; raise a `DocumentLoadError` subclass if invalid."""
    if not data:
        raise EmptyDocumentError(f"'{filename}' is empty (0 bytes).")
    size_mb = len(data) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise FileTooLargeError(f"'{filename}' is {size_mb:.1f} MB; the limit is {max_size_mb} MB per file.")
    if not data.lstrip()[:5].startswith(b"%PDF"):
        raise DocumentLoadError(f"'{filename}' does not look like a valid PDF file.")


def load_pdf_bytes(data: bytes, filename: str, max_size_mb: int = 20) -> list[Document]:
    """Load a PDF from raw bytes. Returns one Document per non-empty page with 1-based `page` metadata."""
    validate_pdf_bytes(data, filename, max_size_mb)

    # PyPDFLoader needs a path, so write the bytes to a temporary file.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        raw_pages = PyPDFLoader(tmp_path).load()
    except Exception as exc:  # pypdf raises many different error types for broken files
        logger.warning("Failed to parse %s: %s", filename, exc)
        raise DocumentLoadError(f"'{filename}' could not be read. It may be corrupted or password-protected.") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    pages: list[Document] = []
    for index, page in enumerate(raw_pages):
        text = (page.page_content or "").strip()
        if not text:
            continue
        zero_based = page.metadata.get("page", index)
        pages.append(
            Document(
                page_content=text,
                metadata={"source": filename, "page": int(zero_based) + 1, "type": "pdf"},
            )
        )

    if not pages:
        raise EmptyDocumentError(
            f"'{filename}' has no extractable text. It is probably a scanned image PDF (OCR is not supported yet)."
        )
    logger.info("Loaded %s: %d/%d pages with text", filename, len(pages), len(raw_pages))
    return pages


def load_pdf_file(path: str | Path, max_size_mb: int = 20) -> list[Document]:
    """Convenience wrapper: load a PDF from disk."""
    path = Path(path)
    return load_pdf_bytes(path.read_bytes(), path.name, max_size_mb)


def parse_urls(text: str) -> tuple[list[str], list[str]]:
    """Split user input into (valid_urls, invalid_entries). One URL per line; duplicates removed."""
    valid: list[str] = []
    invalid: list[str] = []
    for line in (text or "").splitlines():
        entry = line.strip()
        if not entry:
            continue
        if _URL_RE.match(entry):
            if entry not in valid:
                valid.append(entry)
        else:
            invalid.append(entry)
    return valid, invalid


def load_url(url: str, timeout: int = 15) -> list[Document]:
    """Fetch a web page and return it as a single Document with `source` = URL."""
    try:
        loader = WebBaseLoader(url, requests_kwargs={"timeout": timeout}, raise_for_status=True)
        docs = loader.load()
    except Exception as exc:
        logger.warning("Failed to load %s: %s", url, exc)
        raise URLLoadError(f"Could not load {url}. Check the address and that the page is publicly reachable.") from exc

    # Collapse the whitespace that HTML extraction leaves behind.
    text = re.sub(r"\n\s*\n+", "\n\n", "\n".join(d.page_content for d in docs)).strip()
    if len(text) < 50:
        raise URLLoadError(f"{url} has no readable text (it may require JavaScript or a login).")

    title = (docs[0].metadata.get("title") or "").strip() if docs else ""
    return [Document(page_content=text, metadata={"source": url, "page": None, "title": title, "type": "url"})]


def load_markdown_sections(path: str | Path) -> list[Document]:
    """Load a bundled Markdown sample, treating each `## ` section as one page so citations stay precise."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    sections = [s.strip() for s in re.split(r"\n(?=## )", text) if s.strip()]
    return [
        Document(page_content=section, metadata={"source": path.name, "page": number, "type": "sample"})
        for number, section in enumerate(sections, start=1)
    ]
