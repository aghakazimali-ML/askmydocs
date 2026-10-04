"""Generate a few starter questions from the indexed documents."""

from __future__ import annotations

import json
import logging
import re

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from src.chain import format_docs
from src.prompts import SUGGESTION_PROMPT

logger = logging.getLogger(__name__)


def sample_chunks(chunks: list[Document], n: int = 6) -> list[Document]:
    """Pick up to `n` chunks spread evenly across the corpus (start, middle, end)."""
    if len(chunks) <= n:
        return list(chunks)
    step = len(chunks) / n
    return [chunks[int(i * step)] for i in range(n)]


def parse_questions(text: str, limit: int = 3) -> list[str]:
    """Extract questions from the model output: a JSON list if present, otherwise one question per line."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    questions: list[str] = []
    if match:
        try:
            data = json.loads(match.group(0))
            questions = [str(q).strip() for q in data if str(q).strip()]
        except json.JSONDecodeError:
            questions = []
    if not questions:
        lines = [re.sub(r"^[\s\-\*\d\.\)\"]+|[\",]+$", "", line).strip() for line in text.splitlines()]
        questions = [line for line in lines if line.endswith("?")]
    return questions[:limit]


def generate_suggested_questions(llm: BaseChatModel, chunks: list[Document], n: int = 3) -> list[str]:
    """Ask the LLM for `n` starter questions. Returns [] on any failure (suggestions are optional)."""
    if not chunks:
        return []
    try:
        chain = SUGGESTION_PROMPT | llm | StrOutputParser()
        output = chain.invoke({"context": format_docs(sample_chunks(chunks))})
        return parse_questions(output, limit=n)
    except Exception as exc:  # suggestions must never break the main flow
        logger.warning("Could not generate suggested questions: %s", exc)
        return []
