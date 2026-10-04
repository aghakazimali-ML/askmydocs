"""Reusable Streamlit UI pieces: CSS, sidebar, empty state, source cards, suggestions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from src.chain import format_source_label
from src.config import CHAT_MODELS, PROVIDER_LABELS, Settings

_CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 900px;}
.amd-hero h1 {margin-bottom: 0.2rem;}
.amd-hero p {color: #6B7280; margin-top: 0;}
.amd-steps {display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.5rem 0;}
.amd-step {background: #F5F6FB; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.1rem;}
.amd-step .num {display: inline-block; width: 28px; height: 28px; line-height: 28px; text-align: center;
  border-radius: 50%; background: #4F46E5; color: white; font-weight: 700; margin-bottom: .5rem;}
.amd-step h4 {margin: .2rem 0;}
.amd-step p {color: #4B5563; font-size: .9rem; margin: 0;}
.amd-source {border-left: 3px solid #4F46E5; padding: .4rem .8rem; margin: .5rem 0; background: #F9FAFB;
  border-radius: 0 8px 8px 0;}
.amd-source .label {font-weight: 600; font-size: .9rem;}
.amd-source .preview {color: #4B5563; font-size: .85rem; margin-top: .2rem;}
.amd-doc {font-size: .85rem; padding: .15rem 0; overflow-wrap: anywhere;}
@media (max-width: 640px) {.amd-steps {grid-template-columns: 1fr;}}
</style>
"""


@dataclass
class SidebarState:
    """Everything the user chose in the sidebar during this run."""

    provider: str
    model: str
    api_key: str
    temperature: float
    chunk_size: int
    chunk_overlap: int
    top_k: int
    search_type: str
    uploaded_files: list[Any] = field(default_factory=list)
    urls_text: str = ""
    process_clicked: bool = False
    clear_clicked: bool = False
    reset_clicked: bool = False


def inject_css() -> None:
    """Inject the app's custom CSS."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header() -> None:
    """Title and tagline."""
    st.markdown(
        "<div class='amd-hero'><h1>📚 AskMyDocs</h1>"
        "<p>Chat with your PDFs and web pages. Every answer is grounded in your documents, with citations.</p></div>",
        unsafe_allow_html=True,
    )


def render_sidebar(settings: Settings, indexed_documents: list[str]) -> SidebarState:
    """Draw the sidebar and return the user's selections."""
    with st.sidebar:
        st.header("⚙️ Settings")
        providers = list(PROVIDER_LABELS)
        provider = st.selectbox(
            "LLM provider",
            providers,
            index=providers.index(settings.default_provider),
            format_func=PROVIDER_LABELS.get,
        )
        models = list(dict.fromkeys([settings.chat_model_for(provider), *CHAT_MODELS[provider]]))
        model = st.selectbox("Model", models, index=0)
        api_key = st.text_input(
            f"{PROVIDER_LABELS[provider]} API key",
            type="password",
            placeholder="Leave empty to use .env / secrets",
            help="Your key is only kept in this browser session and never stored on disk.",
        )
        temperature = st.slider("Temperature", 0.0, 1.0, float(settings.temperature), 0.05)

        with st.expander("Retrieval & chunking", expanded=False):
            chunk_size = st.number_input("Chunk size", 200, 4000, settings.chunk_size, 50)
            chunk_overlap = st.number_input("Chunk overlap", 0, 1000, settings.chunk_overlap, 10)
            top_k = st.slider("Top-k chunks", 1, 10, settings.top_k)
            search_type = st.radio(
                "Search type",
                ["similarity", "mmr"],
                index=0 if settings.search_type == "similarity" else 1,
                horizontal=True,
                help="MMR (max marginal relevance) favours diverse chunks over near-duplicates.",
            )

        st.header("📂 Documents")
        uploaded_files = st.file_uploader(
            f"Upload PDFs (max {settings.max_file_size_mb} MB each)",
            type=["pdf"],
            accept_multiple_files=True,
        )
        urls_text = st.text_area("…or paste URLs (one per line)", placeholder="https://example.com/article", height=90)

        process_clicked = st.button("🚀 Process documents", type="primary", width="stretch")
        col1, col2 = st.columns(2)
        clear_clicked = col1.button("🧹 Clear chat", width="stretch")
        reset_clicked = col2.button("♻️ Reset all", width="stretch", help="Clears chat, index and saved index.")

        if indexed_documents:
            st.subheader(f"Indexed ({len(indexed_documents)})")
            for name in indexed_documents:
                icon = "🌐" if name.startswith("http") else "📄"
                st.markdown(f"<div class='amd-doc'>{icon} {name}</div>", unsafe_allow_html=True)

    return SidebarState(
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=temperature,
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
        top_k=int(top_k),
        search_type=search_type,
        uploaded_files=list(uploaded_files or []),
        urls_text=urls_text,
        process_clicked=process_clicked,
        clear_clicked=clear_clicked,
        reset_clicked=reset_clicked,
    )


def render_empty_state() -> None:
    """'How it works' screen shown before any document is indexed."""
    st.markdown(
        """
<div class='amd-steps'>
  <div class='amd-step'><div class='num'>1</div><h4>Upload</h4>
    <p>Add one or more PDFs, or paste web page URLs in the sidebar.</p></div>
  <div class='amd-step'><div class='num'>2</div><h4>Process</h4>
    <p>Click <b>Process documents</b>. Text is split into chunks and embedded into a FAISS index.</p></div>
  <div class='amd-step'><div class='num'>3</div><h4>Ask</h4>
    <p>Chat with your documents. Every answer cites the file and page it came from.</p></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.info("👈 Start by adding your API key and documents in the sidebar. Gemini has a free tier.")


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Show cited chunks in a collapsible 'Sources' section."""
    if not sources:
        return
    with st.expander(f"📎 Sources ({len(sources)})"):
        for src in sources:
            label = format_source_label(src["source"], src.get("page"))
            # Escape HTML in previews so document text cannot inject markup.
            preview = (src.get("preview") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(
                f"<div class='amd-source'><div class='label'>{label}</div><div class='preview'>{preview}</div></div>",
                unsafe_allow_html=True,
            )


def render_processing_summary(summary: dict[str, int]) -> None:
    """Show counts after a processing run."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Files / URLs", summary.get("files", 0))
    c2.metric("Pages", summary.get("pages", 0))
    c3.metric("Chunks", summary.get("chunks", 0))


def render_suggestions(questions: list[str]) -> str | None:
    """Render starter questions as buttons; return the clicked question, if any."""
    if not questions:
        return None
    st.caption("💡 Try asking")
    clicked = None
    for i, (col, question) in enumerate(zip(st.columns(len(questions)), questions)):
        if col.button(question, key=f"suggestion_{i}", width="stretch"):
            clicked = question
    return clicked
