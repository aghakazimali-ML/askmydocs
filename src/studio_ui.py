"""Streamlit rendering for the Studio and Library tabs."""

from __future__ import annotations

import html
import logging
import random
from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel

from src.llm import describe_provider_error
from src.studio import (
    TOOLS,
    WRITER_FORMATS,
    WRITER_TONES,
    StudioError,
    chunks_for,
    library_stats,
    mindmap_to_dot,
    run_tool,
    top_keywords,
)

logger = logging.getLogger(__name__)


def _tool_options(tool_key: str, documents: list[str]) -> tuple[list[str], dict[str, Any]]:
    """Draw the option controls for a tool and return (selected documents, options)."""
    min_docs = TOOLS[tool_key].min_docs
    default_docs = documents if min_docs > 1 or len(documents) <= 3 else documents[:1]
    selected = st.multiselect(
        "Documents", documents, default=default_docs, key=f"docs_{tool_key}",
        help="Leave all selected to work across your whole library.",
    )
    options: dict[str, Any] = {}
    cols = st.columns(3)
    if tool_key == "summary":
        options["length"] = cols[0].select_slider("Length", ["short", "medium-length", "detailed"], value="medium-length")
    elif tool_key == "quiz":
        options["count"] = cols[0].slider("Questions", 3, 10, 5)
        options["difficulty"] = cols[1].segmented_control("Difficulty", ["easy", "medium", "hard"], default="medium") or "medium"
    elif tool_key == "flashcards":
        options["count"] = cols[0].slider("Cards", 5, 20, 10)
    elif tool_key == "faq":
        options["count"] = cols[0].slider("Questions", 3, 10, 6)
    elif tool_key == "writer":
        options["format"] = cols[0].selectbox("Format", WRITER_FORMATS)
        options["tone"] = cols[1].selectbox("Tone", WRITER_TONES)
        options["instructions"] = st.text_input(
            "Extra instructions (optional)", placeholder="e.g. address it to our investors, keep it under 200 words"
        )
    return selected, options


def render_studio(chunks: list[Document], get_llm: Callable[[], BaseChatModel | None], language: str) -> None:
    documents = list(dict.fromkeys(c.metadata.get("source", "unknown") for c in chunks))
    tool_key = st.pills(
        "Choose a tool", list(TOOLS), format_func=lambda k: TOOLS[k].label, default="summary", key="studio_tool"
    ) or "summary"
    tool = TOOLS[tool_key]
    st.markdown(f"<div class='amd-tooldesc'>{tool.description}</div>", unsafe_allow_html=True)

    if len(documents) < tool.min_docs:
        st.info(f"{tool.label} needs at least {tool.min_docs} documents. Add another PDF or URL in the sidebar.")
        return

    with st.container(border=True):
        selected, options = _tool_options(tool_key, documents)
        options["language"] = language
        generate = st.button(f"Generate {tool.label}", type="primary", key=f"gen_{tool_key}", disabled=not selected)

    if generate:
        llm = get_llm()
        if llm is not None:
            with st.spinner(f"Creating your {tool.label.split(' ', 1)[1].lower()}…"):
                try:
                    result = run_tool(llm, tool_key, chunks_for(chunks, selected), options)
                    st.session_state.studio[tool_key] = result
                    st.session_state.quiz_answers, st.session_state.quiz_submitted = {}, False
                    st.session_state.card_idx, st.session_state.card_flipped = 0, False
                except StudioError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    logger.exception("Studio tool %s failed", tool_key)
                    st.error(describe_provider_error(exc))

    result = st.session_state.studio.get(tool_key)
    if not result:
        return
    st.caption("Based on: " + ", ".join(result["documents"]))
    output = tool.output
    if output == "quiz":
        _render_quiz(result["data"])
    elif output == "flashcards":
        _render_flashcards(result["data"])
    elif output == "mindmap":
        with st.container(border=True):
            st.graphviz_chart(mindmap_to_dot(result["data"]))
    else:
        with st.container(border=True):
            st.markdown(result["markdown"])
    st.download_button(
        "⬇️ Download (Markdown)", result["markdown"], file_name=f"askmydocs_{tool_key}.md",
        mime="text/markdown", key=f"dl_{tool_key}",
    )


def _render_quiz(quiz: list[dict[str, Any]]) -> None:
    if not st.session_state.quiz_submitted:
        with st.form("quiz_form"):
            answers = {
                n: st.radio(
                    f"**{n + 1}. {q['question']}**", range(len(q["options"])), index=None,
                    format_func=lambda i, q=q: q["options"][i], key=f"quiz_q{n}",
                )
                for n, q in enumerate(quiz)
            }
            if st.form_submit_button("Check my answers", type="primary"):
                st.session_state.quiz_answers = answers
                st.session_state.quiz_submitted = True
                st.rerun()
        return

    answers = st.session_state.quiz_answers
    score = sum(answers.get(n) == q["answer_index"] for n, q in enumerate(quiz))
    pct = round(100 * score / len(quiz))
    with st.container(border=True):
        col1, col2 = st.columns([1, 3], vertical_alignment="center")
        col1.markdown(f"<div class='amd-score'>{score}/{len(quiz)}</div>", unsafe_allow_html=True)
        col2.progress(pct / 100, text=f"{pct}% correct" + (" 🎉 Great job!" if pct >= 80 else " Keep going, review the answers below."))
    if pct >= 80 and not st.session_state.get("quiz_celebrated"):
        st.balloons()
        st.session_state.quiz_celebrated = True

    for n, q in enumerate(quiz):
        chosen = answers.get(n)
        correct = q["options"][q["answer_index"]]
        with st.container(border=True):
            st.markdown(f"**{n + 1}. {q['question']}**")
            if chosen == q["answer_index"]:
                st.success(f"✅ {correct}")
            else:
                picked = q["options"][chosen] if chosen is not None else "no answer"
                st.error(f"❌ You chose: {picked}")
                st.info(f"Correct answer: **{correct}**")
            if q["explanation"]:
                st.caption(q["explanation"])

    if st.button("🔁 Retake quiz"):
        st.session_state.quiz_submitted = False
        st.session_state.quiz_answers = {}
        st.session_state.quiz_celebrated = False
        for n in range(len(quiz)):
            st.session_state.pop(f"quiz_q{n}", None)
        st.rerun()


def _render_flashcards(cards: list[dict[str, str]]) -> None:
    idx = st.session_state.card_idx % len(cards)
    flipped = st.session_state.card_flipped
    card = cards[idx]
    side, text = ("Answer", card["back"]) if flipped else ("Question", card["front"])
    st.markdown(
        f"<div class='amd-flash{' back' if flipped else ''}'><div><small>{side} · {idx + 1} / {len(cards)}</small>"
        f"{html.escape(text)}</div></div>",
        unsafe_allow_html=True,
    )
    st.progress((idx + 1) / len(cards))
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("◀ Previous", width="stretch"):
        st.session_state.card_idx, st.session_state.card_flipped = (idx - 1) % len(cards), False
        st.rerun()
    if c2.button("🔄 Flip", type="primary", width="stretch"):
        st.session_state.card_flipped = not flipped
        st.rerun()
    if c3.button("Next ▶", width="stretch"):
        st.session_state.card_idx, st.session_state.card_flipped = (idx + 1) % len(cards), False
        st.rerun()
    if c4.button("🔀 Shuffle", width="stretch"):
        random.shuffle(cards)
        st.session_state.card_idx, st.session_state.card_flipped = 0, False
        st.rerun()


def render_library(chunks: list[Document]) -> None:
    rows = library_stats(chunks)
    st.markdown("<div class='amd-section'>Documents</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='amd-section'>Size by document (words)</div>", unsafe_allow_html=True)
        sizes = pd.DataFrame({"Document": [r["Document"][:40] for r in rows], "Words": [r["Words (approx.)"] for r in rows]})
        st.bar_chart(sizes, x="Document", y="Words", horizontal=True, color="#6366F1")
    with col2:
        st.markdown("<div class='amd-section'>Top keywords</div>", unsafe_allow_html=True)
        keywords = top_keywords(chunks)
        if keywords:
            kw = pd.DataFrame(keywords, columns=["Keyword", "Mentions"])
            st.bar_chart(kw, x="Keyword", y="Mentions", horizontal=True, color="#EC4899")
        else:
            st.caption("Not enough text to find keywords.")
