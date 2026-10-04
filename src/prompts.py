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
    f'- If the context does not contain the answer, reply exactly: "{NOT_FOUND_MESSAGE}"\n'
    "- Be concise. Use bullet points for lists.\n"
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

# How each retrieved chunk is rendered inside {context}.
DOCUMENT_PROMPT = PromptTemplate.from_template("[Source: {source}{page_label}]\n{page_content}")

# 3. Starter questions shown as buttons after processing.
SUGGESTION_PROMPT = PromptTemplate.from_template(
    "Below are excerpts from a user's documents.\n\n{context}\n\n"
    "Write exactly 3 short, specific questions (max 15 words each) that a reader could answer using ONLY "
    "these excerpts. Return them as a JSON list of strings and nothing else, for example:\n"
    '["What is ...?", "How does ...?", "Why did ...?"]'
)
