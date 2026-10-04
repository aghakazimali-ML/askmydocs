"""Reusable Streamlit UI pieces: theme CSS, top bar, sidebar, landing page, source cards, suggestions."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from src.chain import format_source_label
from src.config import CHAT_MODELS, PROVIDER_LABELS, Settings
from src.motion import motion_view
from src.prompts import ANSWER_STYLES, LANGUAGES

_CSS = """
<style>
/* Design tokens: design-system/askmydocs/MASTER.md (generated with UI/UX Pro Max). Flat style, no gradients. */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root {
  --amd-primary: #0F766E; --amd-primary-hover: #115E59; --amd-secondary: #14B8A6; --amd-accent: #EA580C;
  --amd-bg: #F0FDFA; --amd-fg: #134E4A; --amd-ink: #0F172A; --amd-muted: #475569; --amd-line: #CCEFE9; --amd-soft: #F8FAFC;
}
html, body, .stApp, .stMarkdown, button, input, textarea, select, [data-testid="stWidgetLabel"] {font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;}
.stApp {background: #FFFFFF;}
[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 2.6rem; padding-bottom: 4rem; max-width: 1160px;}
#MainMenu, footer {visibility: hidden;}

/* Sidebar */
[data-testid="stSidebar"] {background: var(--amd-bg); border-right: 1px solid var(--amd-line);}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {font-size: .75rem !important; letter-spacing: .1em; text-transform: uppercase;
  color: var(--amd-primary) !important; font-weight: 700 !important; margin-top: .8rem; padding-bottom: .2rem;}
.amd-brand {display: flex; align-items: center; gap: .65rem; margin: .1rem 0 1.1rem;}
.amd-brand svg {flex: none;}
.amd-brand b {font-size: 1.12rem; color: var(--amd-ink); letter-spacing: -.01em;} .amd-brand span {display: block; font-size: .78rem; color: var(--amd-muted);}
.amd-doc {display: flex; gap: .5rem; align-items: center; font-size: .82rem; padding: .5rem .65rem; margin: .3rem 0; color: var(--amd-fg);
  background: #FFFFFF; border: 1px solid var(--amd-line); border-radius: 10px; overflow-wrap: anywhere;}
.amd-doc svg {flex: none; color: var(--amd-primary);}

/* Workspace top bar */
.amd-topbar {display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .2rem 0 1rem;
  border-bottom: 1px solid var(--amd-line); margin-bottom: 1rem;}
.amd-topbar h1 {font-size: 1.55rem !important; font-weight: 800 !important; letter-spacing: -.02em; color: var(--amd-ink); margin: 0; padding: 0 !important;}
.amd-topbar p {margin: .15rem 0 0; color: var(--amd-muted); font-size: .92rem;}
.amd-badge {display: inline-flex; align-items: center; gap: .4rem; font-size: .78rem; font-weight: 600; color: var(--amd-primary);
  background: var(--amd-bg); border: 1px solid var(--amd-line); padding: .3rem .7rem; border-radius: 999px; white-space: nowrap;}
.amd-badge i {width: 7px; height: 7px; border-radius: 50%; background: var(--amd-secondary); display: inline-block;}

/* Tabs: segmented control */
.stTabs [role="tablist"] {gap: .25rem; background: var(--amd-soft); padding: .3rem; border-radius: 12px; width: fit-content; max-width: 100%;
  overflow-x: auto; border: 1px solid var(--amd-line) !important; box-shadow: none !important; margin-bottom: .8rem;}
.stTabs [role="tab"] {padding: .45rem 1.05rem; border-radius: 9px; border: none !important; cursor: pointer; transition: background-color .18s ease;}
.stTabs [role="tab"] p {font-weight: 600; font-size: .93rem; color: var(--amd-muted);}
.stTabs [role="tab"]:hover {background: #FFFFFF;}
.stTabs [role="tab"][aria-selected="true"] {background: var(--amd-primary);}
.stTabs [role="tab"][aria-selected="true"] p, .stTabs [role="tab"][aria-selected="true"] span {color: #FFFFFF !important;}
.stTabs [role="tab"] > div:not([data-testid]) {display: none;}

/* Chat */
[data-testid="stChatMessage"] {border-radius: 14px; padding: .9rem 1.1rem; border: 1px solid var(--amd-line); background: #FFFFFF; margin-bottom: .6rem;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {background: var(--amd-bg);}

/* Buttons and inputs */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {border-radius: 10px; font-weight: 600; min-height: 44px;
  transition: background-color .18s ease, border-color .18s ease, color .18s ease;}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {background: var(--amd-primary); border-color: var(--amd-primary); color: #FFFFFF;}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {background: var(--amd-primary-hover); border-color: var(--amd-primary-hover);}
[data-testid="stBaseButton-secondary"]:hover {border-color: var(--amd-secondary); color: var(--amd-primary);}
button:focus-visible {outline: 3px solid var(--amd-secondary) !important; outline-offset: 2px;}

/* Sources and Studio */
.amd-source {border-left: 3px solid var(--amd-accent); padding: .5rem .85rem; margin: .5rem 0; background: var(--amd-soft); border-radius: 0 10px 10px 0;}
.amd-source .label {font-weight: 600; font-size: .88rem; color: var(--amd-fg);}
.amd-source .preview {color: var(--amd-muted); font-size: .84rem; margin-top: .2rem;}
.amd-tooldesc {color: var(--amd-muted); font-size: .93rem; margin: .1rem 0 .7rem;}
.amd-section {font-size: .75rem; letter-spacing: .1em; text-transform: uppercase; color: var(--amd-primary); font-weight: 700; margin: 1.2rem 0 .4rem;}
.amd-score {font-size: 2.6rem; font-weight: 800; color: var(--amd-primary); font-variant-numeric: tabular-nums;}

@media (prefers-reduced-motion: reduce) {* {transition: none !important;}}
@media (max-width: 760px) {.amd-topbar {flex-direction: column; align-items: flex-start;}}
</style>
"""

_LOGO = (
    "<svg width='38' height='38' viewBox='0 0 38 38' aria-hidden='true'><rect width='38' height='38' rx='10' fill='#0F766E'/>"
    "<path d='M11 11.5h10.5l5.5 5.5v9.5a1.5 1.5 0 0 1-1.5 1.5h-14.5a1.5 1.5 0 0 1-1.5-1.5v-13.5a1.5 1.5 0 0 1 1.5-1.5z' "
    "fill='none' stroke='#fff' stroke-width='1.8' stroke-linejoin='round'/>"
    "<path d='M14.5 20h9M14.5 23.5h6' stroke='#fff' stroke-width='1.8' stroke-linecap='round'/>"
    "<circle cx='26.5' cy='11.5' r='3.5' fill='#EA580C'/></svg>"
)
_FILE_ICON = (
    "<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' aria-hidden='true'>"
    "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><path d='M14 2v6h6'/></svg>"
)
_LINK_ICON = (
    "<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' aria-hidden='true'>"
    "<circle cx='12' cy='12' r='10'/><path d='M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20'/></svg>"
)


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
    answer_style: str = "Concise"
    language: str = "English"
    uploaded_files: list[Any] = field(default_factory=list)
    urls_text: str = ""
    process_clicked: bool = False
    clear_clicked: bool = False
    reset_clicked: bool = False


def inject_css() -> None:
    """Inject the app's custom CSS."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header(documents: int) -> None:
    """Flat workspace top bar shown once documents are indexed."""
    plural = "s" if documents != 1 else ""
    st.markdown(
        "<div class='amd-topbar'><div><h1>Your workspace</h1>"
        "<p>Chat with your library, or open Studio to summarise, quiz and draft.</p></div>"
        f"<span class='amd-badge'><i></i>{documents} document{plural} indexed</span></div>",
        unsafe_allow_html=True,
    )


def render_sidebar(settings: Settings, indexed_documents: list[str]) -> SidebarState:
    """Draw the sidebar and return the user's selections."""
    with st.sidebar:
        st.markdown(
            f"<div class='amd-brand'>{_LOGO}<div><b>AskMyDocs</b><span>Answers from your documents</span></div></div>",
            unsafe_allow_html=True,
        )

        st.header("Documents")
        uploaded_files = st.file_uploader(
            f"Upload PDFs (max {settings.max_file_size_mb} MB each)",
            type=["pdf"],
            accept_multiple_files=True,
        )
        urls_text = st.text_area("…or paste URLs (one per line)", placeholder="https://example.com/article", height=80)
        process_clicked = st.button("Process documents", type="primary", width="stretch", icon=":material/bolt:")

        if indexed_documents:
            st.header(f"Library ({len(indexed_documents)})")
            for name in indexed_documents:
                icon = _LINK_ICON if name.startswith("http") else _FILE_ICON
                st.markdown(f"<div class='amd-doc'>{icon} {html.escape(name)}</div>", unsafe_allow_html=True)

        st.header("Assistant")
        answer_style = st.selectbox("Answer style", list(ANSWER_STYLES), help="How chat answers are written.")
        language = st.selectbox("Answer language", LANGUAGES, help="Chat answers and Studio results use this language.")

        st.header("Model")
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
            placeholder="Optional if the app has a key",
            help="Your key is only kept in this browser session and never stored on disk.",
        )
        temperature = st.slider("Creativity (temperature)", 0.0, 1.0, float(settings.temperature), 0.05)

        with st.expander("Advanced retrieval", expanded=False):
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

        col1, col2 = st.columns(2)
        clear_clicked = col1.button("Clear chat", width="stretch", icon=":material/delete_sweep:")
        reset_clicked = col2.button("Reset", width="stretch", icon=":material/restart_alt:", help="Clears chat, Studio results and the index.")

    return SidebarState(
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=temperature,
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
        top_k=int(top_k),
        search_type=search_type,
        answer_style=answer_style,
        language=language,
        uploaded_files=list(uploaded_files or []),
        urls_text=urls_text,
        process_clicked=process_clicked,
        clear_clicked=clear_clicked,
        reset_clicked=reset_clicked,
    )


def render_empty_state() -> bool:
    """Animated landing page (React + Framer Motion). Returns True once per click on 'Try with sample documents'."""
    event = motion_view("landing", key="landing")
    if isinstance(event, dict) and event.get("event") == "sample" and event.get("t") != st.session_state.get("_sample_t"):
        st.session_state["_sample_t"] = event.get("t")
        return True
    return False


def render_stats(stats: dict[str, Any]) -> None:
    """Animated count-up tiles for the indexed library."""
    motion_view("stats", key="stats", stats=stats)


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Show cited chunks in a collapsible 'Sources' section."""
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})", icon=":material/format_quote:"):
        for src in sources:
            label = html.escape(format_source_label(src["source"], src.get("page")))
            # Escape HTML in previews so document text cannot inject markup.
            preview = html.escape(src.get("preview") or "")
            st.markdown(
                f"<div class='amd-source'><div class='label'>{label}</div><div class='preview'>{preview}</div></div>",
                unsafe_allow_html=True,
            )


def render_suggestions(questions: list[str]) -> str | None:
    """Render starter questions as buttons; return the clicked question, if any."""
    if not questions:
        return None
    st.caption(":material/lightbulb: Try asking")
    clicked = None
    for i, (col, question) in enumerate(zip(st.columns(len(questions)), questions)):
        if col.button(question, key=f"suggestion_{i}", width="stretch"):
            clicked = question
    return clicked
