"""Reusable Streamlit UI pieces: theme CSS, hero, sidebar, landing page, source cards, suggestions."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from src.chain import format_source_label
from src.config import CHAT_MODELS, PROVIDER_LABELS, Settings
from src.prompts import ANSWER_STYLES, LANGUAGES

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --amd-ink: #0F172A; --amd-muted: #64748B; --amd-line: #E2E8F0; --amd-soft: #F8FAFC;
  --amd-primary: #6366F1; --amd-violet: #8B5CF6; --amd-pink: #EC4899;
  --amd-grad: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #DB2777 100%);
}
html, body, [class*="css"], .stMarkdown, button, input, textarea {font-family: 'Inter', sans-serif;}
.stApp {background: radial-gradient(1200px 500px at 10% -10%, #EEF2FF 0%, transparent 60%),
                    radial-gradient(900px 400px at 100% 0%, #FDF2F8 0%, transparent 55%), #FFFFFF;}
[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 3.2rem; padding-bottom: 4rem; max-width: 1180px;}
#MainMenu, footer {visibility: hidden;}

/* Sidebar */
[data-testid="stSidebar"] {background: linear-gradient(180deg, #F5F3FF 0%, #FFFFFF 45%); border-right: 1px solid var(--amd-line);}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {font-size: .78rem !important; letter-spacing: .08em;
  text-transform: uppercase; color: var(--amd-muted) !important; font-weight: 700 !important; margin-top: .6rem;}
.amd-brand {display: flex; align-items: center; gap: .6rem; margin: .2rem 0 1rem;}
.amd-brand .logo {width: 38px; height: 38px; border-radius: 11px; background: var(--amd-grad); display: grid;
  place-items: center; font-size: 1.2rem; box-shadow: 0 6px 16px rgba(99,102,241,.35);}
.amd-brand b {font-size: 1.15rem; color: var(--amd-ink);} .amd-brand span {display: block; font-size: .75rem; color: var(--amd-muted);}
.amd-doc {display: flex; gap: .5rem; align-items: center; font-size: .82rem; padding: .45rem .6rem; margin: .3rem 0;
  background: #FFFFFF; border: 1px solid var(--amd-line); border-radius: 10px; overflow-wrap: anywhere;}

/* Hero */
.amd-hero {position: relative; overflow: hidden; border-radius: 24px; padding: 2.2rem 2.4rem; color: white;
  background: var(--amd-grad); box-shadow: 0 20px 45px -20px rgba(79,70,229,.6); margin-bottom: 1.4rem;}
.amd-hero::after {content: ""; position: absolute; right: -80px; top: -80px; width: 320px; height: 320px;
  border-radius: 50%; background: rgba(255,255,255,.12);}
.amd-hero h1 {color: white !important; font-size: 2.3rem; font-weight: 800; margin: 0 0 .4rem; letter-spacing: -.02em; padding: 0;}
.amd-hero p {color: rgba(255,255,255,.88); font-size: 1.05rem; margin: 0; max-width: 680px;}
.amd-pills {display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.1rem; position: relative; z-index: 1;}
.amd-pill {background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.3); padding: .3rem .75rem;
  border-radius: 999px; font-size: .8rem; font-weight: 500; backdrop-filter: blur(6px);}
.amd-hero.compact {padding: 1.3rem 1.8rem;} .amd-hero.compact h1 {font-size: 1.6rem;}

/* Cards */
.amd-grid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1rem 0 1.4rem;}
.amd-card {background: white; border: 1px solid var(--amd-line); border-radius: 18px; padding: 1.2rem 1.25rem;
  transition: transform .15s ease, box-shadow .15s ease;}
.amd-card:hover {transform: translateY(-3px); box-shadow: 0 14px 30px -18px rgba(15,23,42,.35);}
.amd-card .ic {width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-size: 1.3rem;
  margin-bottom: .7rem;}
.amd-card h4 {margin: 0 0 .25rem; font-size: 1rem; color: var(--amd-ink); padding: 0;}
.amd-card p {margin: 0; color: var(--amd-muted); font-size: .88rem; line-height: 1.45;}
.amd-steps {display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: .5rem 0 1.2rem;}
.amd-step {display: flex; gap: .8rem; align-items: flex-start; padding: 1rem; border-radius: 16px; background: var(--amd-soft);
  border: 1px dashed #CBD5E1;}
.amd-step .num {flex: none; width: 30px; height: 30px; border-radius: 50%; background: var(--amd-ink); color: white;
  display: grid; place-items: center; font-weight: 700; font-size: .85rem;}
.amd-step b {display: block; color: var(--amd-ink);} .amd-step span {color: var(--amd-muted); font-size: .86rem;}
.amd-section {font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: var(--amd-muted);
  font-weight: 700; margin: 1.2rem 0 .3rem;}

/* Stats */
.amd-stats {display: grid; grid-template-columns: repeat(4, 1fr); gap: .8rem; margin: .2rem 0 1rem;}
.amd-stat {background: white; border: 1px solid var(--amd-line); border-radius: 16px; padding: .9rem 1rem;}
.amd-stat .v {font-size: 1.5rem; font-weight: 800; color: var(--amd-ink); line-height: 1.1;}
.amd-stat .l {font-size: .78rem; color: var(--amd-muted); text-transform: uppercase; letter-spacing: .05em;}

/* Tabs as pills */
.stTabs [role="tablist"] {gap: .4rem; background: #F1F5F9; padding: .35rem; border-radius: 14px; width: fit-content;
  max-width: 100%; overflow-x: auto; border: none !important; box-shadow: none !important; margin-bottom: .6rem;}
.stTabs [role="tab"] {padding: .5rem 1.15rem; border-radius: 10px; border: none !important; cursor: pointer; transition: background .15s;}
.stTabs [role="tab"] p {font-weight: 600; font-size: .95rem; color: var(--amd-muted);}
.stTabs [role="tab"][aria-selected="true"] {background: white; box-shadow: 0 2px 8px rgba(15,23,42,.1);}
.stTabs [role="tab"][aria-selected="true"] p {color: var(--amd-ink);}
.stTabs [role="tab"] > div:not([data-testid]) {display: none;}

/* Chat */
[data-testid="stChatMessage"] {border-radius: 18px; padding: .9rem 1.1rem; border: 1px solid var(--amd-line); background: white; margin-bottom: .6rem;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {background: #EEF2FF; border-color: #E0E7FF;}

/* Buttons */
.stButton button, .stDownloadButton button {border-radius: 12px; font-weight: 600;}
[data-testid="stBaseButton-primary"] {background: var(--amd-grad); border: none; box-shadow: 0 8px 20px -10px rgba(124,58,237,.8);}
[data-testid="stBaseButton-primary"]:hover {filter: brightness(1.07);}

/* Sources */
.amd-source {border-left: 3px solid var(--amd-primary); padding: .5rem .85rem; margin: .5rem 0; background: var(--amd-soft);
  border-radius: 0 10px 10px 0;}
.amd-source .label {font-weight: 600; font-size: .88rem;}
.amd-source .preview {color: #475569; font-size: .84rem; margin-top: .2rem;}

/* Studio */
.amd-flash {border-radius: 22px; min-height: 210px; display: grid; place-items: center; text-align: center; padding: 2rem;
  font-size: 1.25rem; font-weight: 600; color: white; background: var(--amd-grad); box-shadow: 0 18px 40px -22px rgba(79,70,229,.8);}
.amd-flash.back {background: linear-gradient(135deg, #0F766E 0%, #0EA5E9 100%); font-weight: 500; font-size: 1.1rem;}
.amd-flash small {display: block; font-size: .72rem; letter-spacing: .1em; text-transform: uppercase; opacity: .75; margin-bottom: .6rem;}
.amd-score {font-size: 2.6rem; font-weight: 800; background: var(--amd-grad); -webkit-background-clip: text; background-clip: text; color: transparent;}
.amd-tooldesc {color: var(--amd-muted); font-size: .92rem; margin: .2rem 0 .6rem;}

@media (max-width: 760px) {
  .amd-grid, .amd-steps {grid-template-columns: 1fr;} .amd-stats {grid-template-columns: repeat(2, 1fr);}
  .amd-hero {padding: 1.5rem;} .amd-hero h1 {font-size: 1.7rem;}
}
</style>
"""

FEATURES = [
    ("💬", "#EEF2FF", "Chat with citations", "Ask anything. Every answer points to the exact file and page."),
    ("📝", "#FDF2F8", "Instant summaries", "TL;DR, key points and takeaways for one or all documents."),
    ("🧠", "#ECFDF5", "Quizzes & flashcards", "Turn any PDF into a scored quiz or a deck of study cards."),
    ("🗺️", "#FFF7ED", "Mind maps", "See the structure of a document as a visual map."),
    ("⚖️", "#F0F9FF", "Compare documents", "Side-by-side table of what two documents agree and differ on."),
    ("✍️", "#F5F3FF", "AI writer", "Draft emails, reports, LinkedIn posts and meeting notes from your files."),
]


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


def render_header(compact: bool = False) -> None:
    """Gradient hero banner. Compact once documents are loaded so the workspace gets the space."""
    subtitle = (
        "Your AI research assistant for PDFs and web pages. Chat, summarize, quiz yourself, map ideas and draft "
        "content, all grounded in your own documents."
    )
    pills = ""
    if not compact:
        items = ["🔒 Grounded answers", "📎 Page citations", "🌍 10 languages", "🧠 Study tools", "⚡ Gemini & OpenAI"]
        pills = "<div class='amd-pills'>" + "".join(f"<span class='amd-pill'>{p}</span>" for p in items) + "</div>"
    st.markdown(
        f"<div class='amd-hero{' compact' if compact else ''}'><h1>📚 AskMyDocs</h1><p>{subtitle}</p>{pills}</div>",
        unsafe_allow_html=True,
    )


def render_sidebar(settings: Settings, indexed_documents: list[str]) -> SidebarState:
    """Draw the sidebar and return the user's selections."""
    with st.sidebar:
        st.markdown(
            "<div class='amd-brand'><div class='logo'>📚</div><div><b>AskMyDocs</b>"
            "<span>Chat with your documents</span></div></div>",
            unsafe_allow_html=True,
        )

        st.header("📂 Documents")
        uploaded_files = st.file_uploader(
            f"Upload PDFs (max {settings.max_file_size_mb} MB each)",
            type=["pdf"],
            accept_multiple_files=True,
        )
        urls_text = st.text_area("…or paste URLs (one per line)", placeholder="https://example.com/article", height=80)
        process_clicked = st.button("🚀 Process documents", type="primary", width="stretch")

        if indexed_documents:
            st.header(f"Library ({len(indexed_documents)})")
            for name in indexed_documents:
                icon = "🌐" if name.startswith("http") else "📄"
                st.markdown(f"<div class='amd-doc'>{icon} {html.escape(name)}</div>", unsafe_allow_html=True)

        st.header("🎛️ Assistant")
        answer_style = st.selectbox("Answer style", list(ANSWER_STYLES), help="How chat answers are written.")
        language = st.selectbox("Answer language", LANGUAGES, help="Chat answers and Studio results use this language.")

        st.header("⚙️ Model")
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
        clear_clicked = col1.button("🧹 Clear chat", width="stretch")
        reset_clicked = col2.button("♻️ Reset all", width="stretch", help="Clears chat, Studio results and the index.")

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
    """Landing page shown before any document is indexed. Returns True when 'Try a sample' is clicked."""
    col1, col2 = st.columns([1, 2], vertical_alignment="center")
    clicked = col1.button("✨ Try it with sample articles", type="primary", width="stretch")
    col2.caption("No PDF handy? Load two Wikipedia articles about AI and explore every feature in one click.")
    cards = "".join(
        f"<div class='amd-card'><div class='ic' style='background:{bg}'>{icon}</div><h4>{title}</h4><p>{text}</p></div>"
        for icon, bg, title, text in FEATURES
    )
    st.markdown(f"<div class='amd-section'>What you can do</div><div class='amd-grid'>{cards}</div>", unsafe_allow_html=True)
    st.markdown(
        """
<div class='amd-section'>How it works</div>
<div class='amd-steps'>
  <div class='amd-step'><div class='num'>1</div><div><b>Add documents</b><span>Upload PDFs or paste web page links in the sidebar.</span></div></div>
  <div class='amd-step'><div class='num'>2</div><div><b>Process</b><span>Text is split, embedded and indexed in seconds.</span></div></div>
  <div class='amd-step'><div class='num'>3</div><div><b>Chat & create</b><span>Ask questions or open the Studio for summaries, quizzes and more.</span></div></div>
</div>
""",
        unsafe_allow_html=True,
    )
    return clicked


def render_stats(stats: dict[str, Any]) -> None:
    """Four headline numbers for the indexed library."""
    items = [("Documents", stats["documents"]), ("Pages", stats["pages"]), ("Words", f"{stats['words']:,}"),
             ("Reading time", f"{stats['minutes']} min")]
    tiles = "".join(f"<div class='amd-stat'><div class='v'>{v}</div><div class='l'>{label}</div></div>" for label, v in items)
    st.markdown(f"<div class='amd-stats'>{tiles}</div>", unsafe_allow_html=True)


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Show cited chunks in a collapsible 'Sources' section."""
    if not sources:
        return
    with st.expander(f"📎 Sources ({len(sources)})"):
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
    st.caption("💡 Try asking")
    clicked = None
    for i, (col, question) in enumerate(zip(st.columns(len(questions)), questions)):
        if col.button(question, key=f"suggestion_{i}", width="stretch"):
            clicked = question
    return clicked
