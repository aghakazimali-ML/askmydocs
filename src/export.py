"""Export the chat (with sources) as a Markdown document."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.chain import format_source_label


def chat_to_markdown(messages: list[dict[str, Any]], documents: list[str] | None = None, now: datetime | None = None) -> str:
    """Render the conversation as Markdown, including the source list under each answer."""
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    lines = ["# AskMyDocs — Chat Export", "", f"_Exported on {timestamp}_", ""]

    if documents:
        lines += ["## Documents", ""] + [f"- {doc}" for doc in documents] + [""]

    lines += ["## Conversation", ""]
    for message in messages:
        speaker = "🧑 **You**" if message["role"] == "user" else "🤖 **AskMyDocs**"
        lines += [f"### {speaker}", "", message["content"].strip(), ""]
        sources = message.get("sources") or []
        if sources:
            lines += ["**Sources**", ""]
            for src in sources:
                lines.append(f"- {format_source_label(src['source'], src.get('page'))}")
                if src.get("preview"):
                    lines.append(f"  > {src['preview']}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
