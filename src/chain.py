"""History-aware RAG chain built with plain LCEL runnables (no legacy chain classes)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableBranch, RunnablePassthrough
from langchain_core.vectorstores import VectorStore

from src.prompts import DOCUMENT_PROMPT, contextualize_prompt, qa_prompt

logger = logging.getLogger(__name__)

PREVIEW_CHARS = 300


def build_retriever(store: VectorStore, k: int = 4, search_type: str = "similarity") -> BaseRetriever:
    """Create a retriever; MMR fetches a larger candidate pool and picks diverse chunks from it."""
    search_kwargs: dict[str, Any] = {"k": k}
    if search_type == "mmr":
        search_kwargs.update(fetch_k=max(20, k * 5), lambda_mult=0.5)
    return store.as_retriever(search_type=search_type, search_kwargs=search_kwargs)


def format_docs(docs: list[Document]) -> str:
    """Render retrieved chunks into one context string, each prefixed with its source and page."""
    parts = []
    for doc in docs:
        page = doc.metadata.get("page")
        parts.append(
            DOCUMENT_PROMPT.format(
                source=doc.metadata.get("source", "unknown"),
                page_label=f", p. {page}" if page is not None else "",
                page_content=doc.page_content,
            )
        )
    return "\n\n---\n\n".join(parts)


def build_history_aware_retriever(llm: BaseChatModel, retriever: BaseRetriever) -> Runnable:
    """Retriever that first rewrites follow-up questions into standalone ones using the chat history.

    Input: {"input": str, "chat_history": list[BaseMessage]} → Output: list[Document]
    """
    rewrite_question = contextualize_prompt | llm | StrOutputParser()
    return RunnableBranch(
        # No history → the question is already standalone; skip the extra LLM call.
        (lambda x: not x.get("chat_history"), (lambda x: x["input"]) | retriever),
        rewrite_question | retriever,
    ).with_config(run_name="history_aware_retriever")


def build_rag_chain(llm: BaseChatModel, retriever: BaseRetriever) -> Runnable:
    """Full conversational RAG chain.

    Input:  {"input": str, "chat_history": list[BaseMessage]}
    Output: {"input", "chat_history", "context": list[Document], "answer": str}
    Streaming the chain yields the `context` first, then the `answer` token by token.
    """
    answer_chain = (
        RunnablePassthrough.assign(context=lambda x: format_docs(x["context"]))
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    return (
        RunnablePassthrough.assign(context=build_history_aware_retriever(llm, retriever))
        .assign(answer=answer_chain)
        .with_config(run_name="askmydocs_rag")
    )


def to_chat_history(messages: list[dict[str, Any]], max_turns: int = 6) -> list[BaseMessage]:
    """Convert stored chat messages ({"role", "content"}) into LangChain messages, keeping the last N turns."""
    history: list[BaseMessage] = []
    for message in messages[-max_turns * 2 :] if max_turns else []:
        if message["role"] == "user":
            history.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            history.append(AIMessage(content=message["content"]))
    return history


def docs_to_sources(docs: list[Document], preview_chars: int = PREVIEW_CHARS) -> list[dict[str, Any]]:
    """Convert retrieved chunks into de-duplicated, JSON-friendly source records for display/export."""
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for doc in docs:
        key = str(doc.metadata.get("chunk_id") or (doc.metadata.get("source"), doc.metadata.get("page"), doc.page_content[:50]))
        if key in seen:
            continue
        seen.add(key)
        text = " ".join(doc.page_content.split())
        sources.append(
            {
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "preview": text[:preview_chars] + ("…" if len(text) > preview_chars else ""),
            }
        )
    return sources


def format_source_label(source: str, page: int | None) -> str:
    """Human-friendly label, e.g. '📄 report.pdf — page 4' or '🌐 https://example.com'."""
    if page is None:
        return f"🌐 {source}"
    return f"📄 {source} — page {page}"


class StreamedAnswer:
    """Iterates over answer tokens from the chain while capturing the retrieved documents.

    Usage: `stream = StreamedAnswer(chain, question, history)`; pass `stream` to `st.write_stream`,
    then read `stream.context` and `stream.answer`.
    """

    def __init__(self, chain: Runnable, question: str, chat_history: list[BaseMessage]) -> None:
        self._chain = chain
        self._payload = {"input": question, "chat_history": chat_history}
        self.context: list[Document] = []
        self.answer: str = ""

    def __iter__(self) -> Iterator[str]:
        for chunk in self._chain.stream(self._payload):
            if "context" in chunk:
                self.context = chunk["context"]
            token = chunk.get("answer")
            if token:
                self.answer += token
                yield token


def ask(chain: Runnable, question: str, chat_history: list[BaseMessage] | None = None) -> dict[str, Any]:
    """Non-streaming helper: run the chain once and return {'answer', 'context'}."""
    result = chain.invoke({"input": question, "chat_history": chat_history or []})
    return {"answer": result["answer"], "context": result["context"]}


