"""Studio tools: summaries, insights, FAQs, quizzes, flashcards, mind maps, comparisons and writing.

Every tool runs one LLM call over an evenly spread sample of the user's chunks, so it stays grounded
in the documents and costs a predictable amount.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from src.chain import format_docs
from src.prompts import (
    COMPARE_PROMPT,
    FAQ_PROMPT,
    FLASHCARD_PROMPT,
    INSIGHTS_PROMPT,
    MINDMAP_PROMPT,
    QUIZ_PROMPT,
    SUMMARY_PROMPT,
    WRITER_PROMPT,
)

MAX_CONTEXT_CHARS = 30_000


class StudioError(ValueError):
    """Raised when the model output cannot be turned into the requested result."""


@dataclass(frozen=True)
class StudioTool:
    key: str
    label: str
    icon: str  # Material Symbols name, rendered by Streamlit as :material/<icon>:
    description: str
    prompt: PromptTemplate
    output: str  # "markdown" | "quiz" | "flashcards" | "mindmap"
    min_docs: int = 1


TOOLS: dict[str, StudioTool] = {
    t.key: t
    for t in [
        StudioTool("summary", "Summary", "summarize", "TL;DR, key points and why it matters.", SUMMARY_PROMPT, "markdown"),
        StudioTool("insights", "Insights", "insights", "Numbers, people, dates, action items and risks.", INSIGHTS_PROMPT, "markdown"),
        StudioTool("quiz", "Quiz", "quiz", "Test yourself with scored multiple-choice questions.", QUIZ_PROMPT, "quiz"),
        StudioTool("flashcards", "Flashcards", "style", "Flip-cards for studying the key concepts.", FLASHCARD_PROMPT, "flashcards"),
        StudioTool("mindmap", "Mind map", "account_tree", "A visual map of the main topics.", MINDMAP_PROMPT, "mindmap"),
        StudioTool("faq", "FAQ", "help", "Questions a reader would ask, answered.", FAQ_PROMPT, "markdown"),
        StudioTool("compare", "Compare", "compare_arrows", "Side-by-side comparison of two or more documents.", COMPARE_PROMPT, "markdown", 2),
        StudioTool("writer", "Writer", "edit_note", "Turn your documents into an email, report, post and more.", WRITER_PROMPT, "markdown"),
    ]
}

WRITER_FORMATS = ["Professional email", "Executive report", "LinkedIn post", "Blog post outline",
                  "Meeting notes", "X / Twitter thread", "Proposal", "Press release"]
WRITER_TONES = ["Professional", "Friendly", "Persuasive", "Neutral", "Enthusiastic"]


# ---------- context selection ----------
def chunks_for(chunks: list[Document], documents: list[str] | None) -> list[Document]:
    """Keep only chunks from the selected documents (all of them when `documents` is empty)."""
    if not documents:
        return list(chunks)
    wanted = set(documents)
    return [c for c in chunks if c.metadata.get("source") in wanted]


def sample_context(chunks: list[Document], max_chars: int = MAX_CONTEXT_CHARS) -> list[Document]:
    """Pick chunks spread evenly across the corpus until `max_chars` is reached, kept in reading order."""
    if not chunks:
        return []
    total = sum(len(c.page_content) for c in chunks)
    if total <= max_chars:
        return list(chunks)
    keep = max(1, int(len(chunks) * max_chars / total))
    step = len(chunks) / keep
    return [chunks[int(i * step)] for i in range(keep)]


def balanced_context(chunks: list[Document], max_chars: int = MAX_CONTEXT_CHARS) -> list[Document]:
    """Give every document an equal share of the budget (used by Compare)."""
    by_doc: dict[str, list[Document]] = defaultdict(list)
    for c in chunks:
        by_doc[c.metadata.get("source", "unknown")].append(c)
    if not by_doc:
        return []
    share = max_chars // len(by_doc)
    return [c for doc_chunks in by_doc.values() for c in sample_context(doc_chunks, share)]


# ---------- parsing ----------
def extract_json(text: str) -> Any:
    """Parse the first JSON object or list in a model reply (tolerates ```json fences and chatter)."""
    cleaned = re.sub(r"```(?:json)?", "", text)
    pairs = sorted((("[", "]"), ("{", "}")), key=lambda p: (cleaned.find(p[0]) == -1, cleaned.find(p[0])))
    for opener, closer in pairs:  # outermost structure first
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise StudioError("The AI returned an unexpected format. Please click Generate again.")


def parse_quiz(text: str) -> list[dict[str, Any]]:
    data = extract_json(text)
    items = data.get("questions", []) if isinstance(data, dict) else data
    quiz = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        options = [str(o).strip() for o in item.get("options", []) if str(o).strip()]
        try:
            answer = int(item.get("answer_index", -1))
        except (TypeError, ValueError):
            continue
        if item.get("question") and len(options) >= 2 and 0 <= answer < len(options):
            quiz.append({
                "question": str(item["question"]).strip(),
                "options": options,
                "answer_index": answer,
                "explanation": str(item.get("explanation", "")).strip(),
                "source": str(item.get("source", "")).strip(),
            })
    if not quiz:
        raise StudioError("Could not build a quiz from these documents. Try again or pick other documents.")
    return quiz


def parse_flashcards(text: str) -> list[dict[str, str]]:
    data = extract_json(text)
    items = data.get("cards", []) if isinstance(data, dict) else data
    cards = [
        {"front": str(i["front"]).strip(), "back": str(i["back"]).strip()}
        for i in (items if isinstance(items, list) else [])
        if isinstance(i, dict) and i.get("front") and i.get("back")
    ]
    if not cards:
        raise StudioError("Could not build flashcards from these documents. Try again.")
    return cards


def parse_mindmap(text: str) -> dict[str, Any]:
    data = extract_json(text)
    if not isinstance(data, dict) or not isinstance(data.get("branches"), list):
        raise StudioError("Could not build a mind map. Try again.")
    branches = [
        {"name": str(b["name"]).strip(), "children": [str(c).strip() for c in b.get("children", []) if str(c).strip()]}
        for b in data["branches"]
        if isinstance(b, dict) and b.get("name")
    ]
    if not branches:
        raise StudioError("Could not build a mind map. Try again.")
    return {"title": str(data.get("title") or "Your documents").strip(), "branches": branches}


_PALETTE = ["#171717", "#2563EB", "#404040", "#1D4ED8", "#525252", "#3B82F6", "#737373"]


def _dot_label(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def mindmap_to_dot(mindmap: dict[str, Any]) -> str:
    """Render a parsed mind map as a Graphviz DOT string (left-to-right, coloured branches)."""
    lines = [
        "digraph G {",
        '  graph [rankdir=LR, bgcolor="transparent", nodesep=0.25, ranksep=0.6, size="12,7"];',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", margin="0.18,0.08", fontsize=11, penwidth=0];',
        '  edge [penwidth=1.6, arrowhead=none];',
        f'  root [label="{_dot_label(mindmap["title"])}", fillcolor="#171717", fontcolor="white", fontsize=14];',
    ]
    for i, branch in enumerate(mindmap["branches"]):
        color = _PALETTE[i % len(_PALETTE)]
        lines.append(f'  b{i} [label="{_dot_label(branch["name"])}", fillcolor="{color}", fontcolor="white"];')
        lines.append(f'  root -> b{i} [color="{color}"];')
        for j, child in enumerate(branch["children"]):
            lines.append(f'  b{i}c{j} [label="{_dot_label(child)}", fillcolor="{color}22", fontcolor="#1F2937"];')
            lines.append(f'  b{i} -> b{i}c{j} [color="{color}"];')
    lines.append("}")
    return "\n".join(lines)


def mindmap_to_markdown(mindmap: dict[str, Any]) -> str:
    lines = [f"# {mindmap['title']}", ""]
    for branch in mindmap["branches"]:
        lines.append(f"- **{branch['name']}**")
        lines += [f"  - {child}" for child in branch["children"]]
    return "\n".join(lines) + "\n"


def quiz_to_markdown(quiz: list[dict[str, Any]]) -> str:
    lines = ["# Quiz", ""]
    for n, q in enumerate(quiz, start=1):
        lines.append(f"**{n}. {q['question']}**")
        lines += [f"- {opt}{' **(correct)**' if i == q['answer_index'] else ''}" for i, opt in enumerate(q["options"])]
        if q["explanation"]:
            lines.append(f"\n_{q['explanation']}_")
        lines.append("")
    return "\n".join(lines)


def flashcards_to_markdown(cards: list[dict[str, str]]) -> str:
    return "# Flashcards\n\n" + "\n".join(f"**{c['front']}**  \n{c['back']}\n" for c in cards)


# ---------- running a tool ----------
def run_tool(
    llm: BaseChatModel,
    tool_key: str,
    chunks: list[Document],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a Studio tool and return {"tool", "markdown", "data"} where `data` is the structured result."""
    tool = TOOLS[tool_key]
    options = dict(options or {})
    if not chunks:
        raise StudioError("No document text available. Process some documents first.")
    documents = sorted({c.metadata.get("source", "unknown") for c in chunks})
    if len(documents) < tool.min_docs:
        raise StudioError(f"{tool.label} needs at least {tool.min_docs} documents. Upload another one.")

    context_docs = balanced_context(chunks) if tool_key == "compare" else sample_context(chunks)
    variables = {
        "context": format_docs(context_docs),
        "language": options.get("language", "English"),
        "length": options.get("length", "medium-length"),
        "count": options.get("count", 5),
        "difficulty": options.get("difficulty", "medium"),
        "documents": ", ".join(documents),
        "format": options.get("format", WRITER_FORMATS[0]),
        "tone": options.get("tone", WRITER_TONES[0]),
        "instructions": options.get("instructions", "") or "none",
    }
    text = (tool.prompt | llm | StrOutputParser()).invoke(
        {k: v for k, v in variables.items() if k in tool.prompt.input_variables}
    )

    if tool.output == "quiz":
        data: Any = parse_quiz(text)
        markdown = quiz_to_markdown(data)
    elif tool.output == "flashcards":
        data = parse_flashcards(text)
        markdown = flashcards_to_markdown(data)
    elif tool.output == "mindmap":
        data = parse_mindmap(text)
        markdown = mindmap_to_markdown(data)
    else:
        data = None
        markdown = text.strip()
    return {"tool": tool_key, "markdown": markdown, "data": data, "documents": documents}


# ---------- library stats (no LLM) ----------
_STOPWORDS = set(
    """a about above after again against all also am an and any are as at be because been before being below
    between both but by can could did do does doing down during each few for from further had has have having he
    her here hers him his how i if in into is it its itself just me more most my no nor not now of off on once only
    or other our ours out over own same she should so some such than that the their theirs them then there these
    they this those through to too under until up very was we were what when where which while who whom why will
    with would you your yours one two may also use used using page pdf www http https com org per new like
    within without however therefore thus via etc""".split()
)


def library_stats(chunks: list[Document]) -> list[dict[str, Any]]:
    """Per-document stats: type, pages, chunks, approximate words and reading time."""
    stats: dict[str, dict[str, Any]] = {}
    for c in chunks:
        name = c.metadata.get("source", "unknown")
        s = stats.setdefault(name, {"pages": set(), "chunks": 0, "words": 0})
        if c.metadata.get("page") is not None:
            s["pages"].add(c.metadata["page"])
        s["chunks"] += 1
        s["words"] += len(c.page_content.split())
    rows = []
    for name, s in stats.items():
        rows.append({
            "Document": name,
            "Type": "Web page" if str(name).startswith("http") else "PDF",
            "Pages": len(s["pages"]) or 1,
            "Chunks": s["chunks"],
            "Words (approx.)": s["words"],
            "Reading time (min)": max(1, round(s["words"] / 230)),
        })
    return rows


def top_keywords(chunks: list[Document], n: int = 15) -> list[tuple[str, int]]:
    """Most frequent meaningful words across the chunks."""
    counter: Counter[str] = Counter()
    for c in chunks:
        for word in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", c.page_content.lower()):
            if word not in _STOPWORDS:
                counter[word] += 1
    return counter.most_common(n)
