"""
Query Rewriter — produce a self-contained standalone query from chat history.

Problem:
    User: "What is the vacation policy?"
    AI:   "Employees receive 20 days..."
    User: "What about managers?"

Retrieval should search:
    "What is the vacation policy for managers?"
NOT:
    "What about managers?"

Architecture:
    Chat history
         ↓
    Query Rewriter (Gemini)
         ↓
    Standalone query
         ↓
    Hybrid Retrieval
"""
from __future__ import annotations

import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY, transport="rest")

_REWRITE_MODEL = genai.GenerativeModel(settings.GENERATION_MODEL)

_SYSTEM_PROMPT = """You are a query preprocessing assistant.
Given a conversation history and the user's latest message, rewrite the
latest message into a self-contained search query that can be understood
without the conversation history. Return ONLY the rewritten query — no
explanations, no surrounding text."""


def rewrite_query(query: str, history: list[dict] | None = None) -> str:
    """
    Parameters
    ----------
    query : str
        The user's latest message.
    history : list[dict], optional
        Previous turns: [{"role": "user"|"ai", "content": "..."}]

    Returns
    -------
    str
        A standalone query suitable for retrieval.
        Falls back to the original query on any error.
    """
    if not history:
        return query

    conversation = "\n".join(
        f"{turn['role'].upper()}: {turn['content']}" for turn in history[-4:]
    )
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"CONVERSATION:\n{conversation}\n\n"
        f"LATEST MESSAGE: {query}\n\n"
        f"STANDALONE QUERY:"
    )

    try:
        response = _REWRITE_MODEL.generate_content(prompt)
        rewritten = response.text.strip()
        return rewritten if rewritten else query
    except Exception:
        return query
