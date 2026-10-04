"""All prompt templates used by AskMyDocs, kept in one place for easy tuning."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate

NOT_FOUND_MESSAGE = "I couldn't find that in your documents."

# 1. Rewrites a follow-up question into a standalone one so retrieval works without the chat history.
CONTEXTUALIZE_SYSTEM_PROMPT = (
    "Given the chat history and the latest user question, which might reference earlier messages "
    "(e.g. 'explain the second point more'), rewrite it as a standalone question that can be understood "
    "without the chat history. Keep names, numbers and key terms. "
    "Do NOT answer the question. Return only the rewritten question, or the original question if it is "
    "already standalone."
)

contextualize_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", CONTEXTUALIZE_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# 2. Strictly grounded answering prompt.
QA_SYSTEM_PROMPT = (
    "You are AskMyDocs, an assistant that answers questions strictly from the user's documents.\n\n"
    "Rules:\n"
    "- Use ONLY the context below. Never use outside knowledge and never invent facts.\n"
    f'- If the context does not contain the answer, reply exactly (in English): "{NOT_FOUND_MESSAGE}"\n'
    "- Answer style: {style}\n"
    "- Write the answer in {language}.\n"
    "- When stating a fact, cite its source inline like (report.pdf, p. 4). For web pages cite the URL, "
    "like (https://example.com).\n\n"
    "Context:\n{context}"
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", QA_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Chat answer styles offered in the UI, mapped to the instruction given to the model.
ANSWER_STYLES: dict[str, str] = {
    "Concise": "Be concise: 2 to 5 sentences or a short bullet list.",
    "Detailed": "Be thorough: explain step by step with headings and bullet points where helpful.",
    "Bullet points": "Answer only with clear, scannable bullet points.",
    "Simple (ELI5)": "Explain in very simple words, as if to a 12-year-old, with one everyday analogy.",
    "Executive": "Lead with a one-line bottom line, then 3 bullets on impact, numbers and next steps.",
}

LANGUAGES = ["English", "Urdu", "Hindi", "Arabic", "Spanish", "French", "German", "Portuguese", "Chinese", "Turkish"]

# How each retrieved chunk is rendered inside {context}.
DOCUMENT_PROMPT = PromptTemplate.from_template("[Source: {source}{page_label}]\n{page_content}")

# 3. Starter questions shown as buttons after processing.
SUGGESTION_PROMPT = PromptTemplate.from_template(
    "Below are excerpts from a user's documents.\n\n{context}\n\n"
    "Write exactly 3 short, specific questions (max 15 words each) that a reader could answer using ONLY "
    "these excerpts. Return them as a JSON list of strings and nothing else, for example:\n"
    '["What is ...?", "How does ...?", "Why did ...?"]'
)

# 4. Studio tools. Each works on a sample of the user's chunks, never on outside knowledge.
_STUDIO_RULES = (
    "Use ONLY the document excerpts below. Never add outside facts. "
    "Write in {language}. Cite sources inline like (file.pdf, p. 3) where useful.\n\n"
    "Excerpts:\n{context}\n\n"
)

SUMMARY_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "Write a {length} summary in Markdown with these sections:\n"
    "### TL;DR\nOne or two sentences.\n"
    "### Key points\nBullet points.\n"
    "### Why it matters\nTwo or three bullets on implications or takeaways."
)

INSIGHTS_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "Extract structured insights in Markdown. Use these sections and skip any that have nothing:\n"
    "### 📊 Key numbers & facts\n### 👥 People & organizations\n### 📅 Dates & deadlines\n"
    "### ✅ Action items\n### ⚠️ Risks & open questions\n"
    "Use short bullet points. Bold the most important figure in each bullet."
)

FAQ_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "Write {count} frequently asked questions a reader would have, each answered from the excerpts. "
    "Format each as '**Q: ...**' on one line followed by 'A: ...' on the next, separated by blank lines."
)

QUIZ_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "Create {count} multiple-choice questions ({difficulty} difficulty) that test understanding of the excerpts. "
    "Return ONLY a JSON list. Each item: "
    '{{"question": str, "options": [4 strings], "answer_index": 0-3, "explanation": str, "source": str}}'
)

FLASHCARD_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "Create {count} study flashcards covering the most important concepts, terms and figures. "
    'Return ONLY a JSON list. Each item: {{"front": short question or term, "back": concise answer}}'
)

MINDMAP_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "Build a mind map of the main topics. Return ONLY JSON: "
    '{{"title": str, "branches": [{{"name": str, "children": [str, ...]}}]}} '
    "with 4 to 7 branches and 2 to 5 short children (max 6 words) each."
)

COMPARE_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "The excerpts come from these documents: {documents}.\n"
    "Compare them in Markdown:\n### At a glance\nA table with one column per document and rows for "
    "purpose, main topics, key numbers and conclusions.\n### Common ground\nBullets.\n"
    "### Key differences\nBullets.\n### Which to read for what\nOne line per document."
)

WRITER_PROMPT = PromptTemplate.from_template(
    _STUDIO_RULES
    + "Using the excerpts, write a {format} in Markdown. Tone: {tone}. "
    "Extra instructions from the user (may be empty): {instructions}\n"
    "Make it ready to use as-is, with no placeholders other than [Name] where a recipient name is needed."
)
