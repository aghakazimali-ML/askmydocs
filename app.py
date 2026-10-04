"""AskMyDocs — Streamlit entry point. UI wiring only; all logic lives in `src/`."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import streamlit as st

from src.chain import StreamedAnswer, build_rag_chain, build_retriever, docs_to_sources, to_chat_history
from src.config import PROVIDER_LABELS, get_settings, setup_logging
from src.export import chat_to_markdown
from src.llm import describe_provider_error, get_chat_model, get_embeddings, resolve_api_key
from src.loaders import DocumentLoadError, load_markdown_sections, load_pdf_bytes, load_url, parse_urls
from src.prompts import NOT_FOUND_MESSAGE
from src.splitter import split_documents
from src.studio import library_stats
from src.studio_ui import render_library, render_studio
from src.suggestions import generate_suggested_questions
from src.ui_components import (
    SidebarState,
    inject_css,
    render_empty_state,
    render_header,
    render_sidebar,
    render_sources,
    render_stats,
    render_suggestions,
)
from src.vectorstore import (
    add_chunks,
    content_hash,
    delete_vectorstore,
    embedding_signature,
    load_vectorstore,
    read_manifest,
    save_vectorstore,
    stored_chunks,
)

st.set_page_config(page_title="AskMyDocs · Chat with your documents", page_icon=":material/description:", layout="wide")
settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("askmydocs")

AVATARS = {"user": ":material/person:", "assistant": ":material/auto_stories:"}

# Bundled offline so the demo works even where outbound requests are blocked.
SAMPLE_FILES = sorted((Path(__file__).parent / "docs" / "samples").glob("*.md"))


# ---------- cached clients ----------
@st.cache_resource(show_spinner=False)
def cached_chat_model(provider: str, model: str, api_key: str, temperature: float):
    return get_chat_model(provider, model, api_key, temperature)


@st.cache_resource(show_spinner=False)
def cached_embeddings(provider: str, model: str, api_key: str):
    return get_embeddings(provider, model, api_key)


# ---------- session state ----------
DEFAULT_STATE: dict[str, Any] = {
    "messages": [],          # [{"role", "content", "sources"}]
    "vectorstore": None,     # FAISS | None
    "file_hashes": {},       # sha256 -> display name (skips re-embedding duplicates)
    "documents": [],         # display names of indexed files/URLs
    "all_chunks": [],        # kept for suggested questions
    "index_signature": None, # "provider:embedding-model" that built the index
    "suggestions": [],
    "last_summary": None,
    "pending_question": None,
    "autoload_checked": False,
    "studio": {},            # tool key -> result from src.studio.run_tool
    "quiz_answers": {},
    "quiz_submitted": False,
}


def init_state() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value


def reset_state(delete_saved: bool) -> None:
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value
    st.session_state.autoload_checked = True
    if delete_saved and settings.persist_index:
        delete_vectorstore(settings.vectorstore_dir)


def secrets_or_none() -> Any:
    """`st.secrets` raises if no secrets file exists; treat that as 'no secrets'."""
    try:
        return dict(st.secrets)
    except Exception:
        return None


def key_for(provider: str, sidebar_key: str) -> str:
    return resolve_api_key(provider, sidebar_key, settings.api_key_for(provider), secrets_or_none())


# ---------- persistence ----------
def try_autoload_index(cfg: SidebarState) -> None:
    """Reload a previously saved FAISS index once per session, if a matching API key is available."""
    if not settings.persist_index or st.session_state.autoload_checked or st.session_state.vectorstore is not None:
        return
    manifest = read_manifest(settings.vectorstore_dir)
    if not manifest:
        st.session_state.autoload_checked = True
        return
    provider = manifest["provider"]
    api_key = key_for(provider, cfg.api_key if cfg.provider == provider else "")
    if not api_key:
        st.sidebar.info(f"A saved index was found. Add your {PROVIDER_LABELS[provider]} key to load it.", icon=":material/database:")
        return
    try:
        embeddings = cached_embeddings(provider, manifest["embedding_model"], api_key)
        st.session_state.vectorstore = load_vectorstore(settings.vectorstore_dir, embeddings)
        st.session_state.documents = manifest.get("documents", [])
        st.session_state.file_hashes = manifest.get("file_hashes", {})
        st.session_state.index_signature = embedding_signature(provider, manifest["embedding_model"])
        st.toast(f"Loaded saved index with {len(st.session_state.documents)} document(s).", icon=":material/database:")
    except Exception as exc:
        logger.exception("Could not load saved index")
        st.sidebar.warning(f"Saved index could not be loaded: {describe_provider_error(exc)}")
    st.session_state.autoload_checked = True


# ---------- ingestion ----------
def process_documents(cfg: SidebarState, api_key: str, samples: list[Path] | None = None) -> None:
    """Load → split → embed → index all new files, URLs and bundled samples, with progress feedback."""
    urls, invalid_urls = parse_urls(cfg.urls_text)
    for entry in invalid_urls:
        st.warning(f"Skipped invalid URL: `{entry}`")
    if not cfg.uploaded_files and not urls and not samples:
        st.warning("Upload at least one PDF or paste a URL first.")
        return
    if cfg.chunk_overlap >= cfg.chunk_size:
        st.error("Chunk overlap must be smaller than chunk size.")
        return

    emb_model = settings.embedding_model_for(cfg.provider)
    signature = embedding_signature(cfg.provider, emb_model)
    if st.session_state.vectorstore is not None and st.session_state.index_signature != signature:
        st.error("The current index was built with a different provider. Switch back, or click **Reset all** first.")
        return

    try:
        embeddings = cached_embeddings(cfg.provider, emb_model, api_key)
    except Exception as exc:
        st.error(describe_provider_error(exc))
        return

    sources: list[tuple[str, str, Any]] = (
        [("pdf", f.name, f) for f in cfg.uploaded_files]
        + [("url", u, u) for u in urls]
        + [("sample", p.name, p) for p in samples or []]
    )
    progress = st.progress(0.0, text="Starting…")
    summary = {"files": 0, "pages": 0, "chunks": 0}
    new_chunks_all = []

    for i, (kind, name, item) in enumerate(sources, start=1):
        progress.progress((i - 1) / len(sources), text=f"Processing {name}…")
        data = item.getvalue() if kind == "pdf" else item.read_text(encoding="utf-8") if kind == "sample" else item
        digest = content_hash(data)
        if digest in st.session_state.file_hashes:
            st.info(f"`{name}` is already indexed, so it was skipped.", icon=":material/skip_next:")
            continue
        try:
            if kind == "pdf":
                docs = load_pdf_bytes(data, name, settings.max_file_size_mb)
            elif kind == "sample":
                docs = load_markdown_sections(item)
            else:
                docs = load_url(item, settings.url_timeout_seconds)
            chunks = split_documents(docs, cfg.chunk_size, cfg.chunk_overlap)
            st.session_state.vectorstore = add_chunks(st.session_state.vectorstore, chunks, embeddings)
        except DocumentLoadError as exc:
            st.error(str(exc), icon=":material/error:")
            continue
        except Exception as exc:
            logger.exception("Embedding failed for %s", name)
            st.error(f"{name}: {describe_provider_error(exc)}", icon=":material/error:")
            if "API key" in describe_provider_error(exc):
                break  # every other file would fail the same way
            continue

        st.session_state.file_hashes[digest] = name
        st.session_state.documents.append(name)
        st.session_state.index_signature = signature
        new_chunks_all.extend(chunks)
        summary["files"] += 1
        summary["pages"] += len(docs)
        summary["chunks"] += len(chunks)

    progress.progress(1.0, text="Done")
    progress.empty()
    if not new_chunks_all:
        return

    st.session_state.all_chunks.extend(new_chunks_all)
    st.session_state.last_summary = summary
    if settings.persist_index:
        _save_index(cfg.provider, emb_model)
    with st.spinner("Generating suggested questions…"):
        try:
            llm = cached_chat_model(cfg.provider, cfg.model, api_key, cfg.temperature)
            st.session_state.suggestions = generate_suggested_questions(llm, st.session_state.all_chunks)
        except Exception as exc:
            logger.warning("Suggestions skipped: %s", exc)
    st.success(f"Indexed {summary['files']} source(s): {summary['pages']} pages, {summary['chunks']} chunks.", icon=":material/check_circle:")


def _save_index(provider: str, emb_model: str) -> None:
    save_vectorstore(
        st.session_state.vectorstore,
        settings.vectorstore_dir,
        {
            "provider": provider,
            "embedding_model": emb_model,
            "documents": st.session_state.documents,
            "file_hashes": st.session_state.file_hashes,
        },
    )


# ---------- chat ----------
def answer_question(question: str, cfg: SidebarState, api_key: str) -> None:
    """Stream an answer for `question` and append both turns to the history."""
    history = to_chat_history(st.session_state.messages, settings.max_history_turns)
    st.session_state.messages.append({"role": "user", "content": question, "sources": []})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(question)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        try:
            llm = cached_chat_model(cfg.provider, cfg.model, api_key, cfg.temperature)
            retriever = build_retriever(st.session_state.vectorstore, cfg.top_k, cfg.search_type)
            chain = build_rag_chain(llm, retriever, cfg.answer_style, cfg.language)
            stream = StreamedAnswer(chain, question, history)
            tokens = iter(stream)
            with st.spinner("Searching your documents…"):
                first = next(tokens, "")  # retrieval happens before the first token arrives
            st.write_stream(_chain_first(first, tokens))
            answer = stream.answer.strip() or NOT_FOUND_MESSAGE
        except Exception as exc:
            logger.exception("Chat failed")
            st.error(describe_provider_error(exc))
            st.session_state.messages.pop()  # drop the unanswered question
            return
        sources = [] if NOT_FOUND_MESSAGE.lower() in answer.lower() else docs_to_sources(stream.context)
        render_sources(sources)
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})


def _chain_first(first: str, rest):
    """Re-attach the first token (consumed while the spinner was shown) to the stream."""
    if first:
        yield first
    yield from rest


def library_summary(chunks) -> dict[str, int]:
    rows = library_stats(chunks)
    words = sum(r["Words (approx.)"] for r in rows)
    return {"documents": len(rows), "pages": sum(r["Pages"] for r in rows), "words": words,
            "minutes": max(1, round(words / 230)) if words else 0}


def render_chat_tab(cfg: SidebarState, api_key: str) -> None:
    history_box = st.container()
    suggestions_box = st.container()
    typed = st.chat_input("Ask a question about your documents…")
    question = typed or st.session_state.pending_question
    st.session_state.pending_question = None

    with history_box:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
                st.markdown(message["content"])
                render_sources(message.get("sources", []))
                if message["role"] == "assistant":
                    st.feedback("thumbs", key=f"fb_{i}")
        if question:
            if not api_key:
                st.error(f"Please add your {PROVIDER_LABELS[cfg.provider]} API key in the sidebar first.")
            else:
                answer_question(question, cfg, api_key)

    if not st.session_state.messages and not question:
        with suggestions_box:
            clicked = render_suggestions(st.session_state.suggestions)
            if clicked:
                st.session_state.pending_question = clicked
                st.rerun()

    if st.session_state.messages:
        with suggestions_box:
            st.download_button(
                "Export chat (Markdown)",
                data=chat_to_markdown(st.session_state.messages, st.session_state.documents),
                file_name="askmydocs_chat.md",
                mime="text/markdown",
                icon=":material/download:",
            )


def workspace_report() -> str:
    """Chat plus every Studio result in one Markdown file."""
    parts = [chat_to_markdown(st.session_state.messages, st.session_state.documents)]
    parts += [result["markdown"] for result in st.session_state.studio.values()]
    return "\n\n---\n\n".join(parts)


def main() -> None:
    init_state()
    inject_css()
    cfg = render_sidebar(settings, st.session_state.documents)
    api_key = key_for(cfg.provider, cfg.api_key)

    if cfg.reset_clicked:
        reset_state(delete_saved=True)
        st.rerun()
    if cfg.clear_clicked:
        st.session_state.messages = []
        st.rerun()

    try_autoload_index(cfg)
    hero, landing = st.empty(), st.empty()  # filled after processing so they reflect the new state

    sample_clicked = False
    if st.session_state.vectorstore is None:
        with landing.container():
            sample_clicked = render_empty_state()

    if cfg.process_clicked or sample_clicked:
        if not api_key:
            st.error(f"Please add your {PROVIDER_LABELS[cfg.provider]} API key in the sidebar or .env file.")
        else:
            process_documents(cfg, api_key, SAMPLE_FILES if sample_clicked and not cfg.process_clicked else None)

    if st.session_state.vectorstore is None:
        return
    with hero.container():
        render_header(len(st.session_state.documents))
    landing.empty()

    chunks = stored_chunks(st.session_state.vectorstore)
    render_stats(library_summary(chunks))

    def get_llm():
        if not api_key:
            st.error(f"Please add your {PROVIDER_LABELS[cfg.provider]} API key in the sidebar first.")
            return None
        return cached_chat_model(cfg.provider, cfg.model, api_key, cfg.temperature)

    chat_tab, studio_tab, library_tab = st.tabs([":material/forum: Chat", ":material/auto_awesome: Studio", ":material/folder_open: Library"])
    with chat_tab:
        render_chat_tab(cfg, api_key)
    with studio_tab:
        render_studio(chunks, get_llm, cfg.language)
    with library_tab:
        render_library(chunks)
        st.download_button(
            "Download workspace report (chat + Studio)",
            data=workspace_report(),
            file_name="askmydocs_report.md",
            mime="text/markdown",
            icon=":material/download:",
        )


main()
