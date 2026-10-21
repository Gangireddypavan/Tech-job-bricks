"""Thin wrapper over the Genie Conversation API for the Ask page."""

import os
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient

SPACE_ID = os.getenv("GENIE_SPACE_ID", "")


@dataclass
class Answer:
    conversation_id: str | None = None
    text: str = ""
    sql: str = ""
    description: str = ""
    data: pd.DataFrame | None = None
    suggestions: list = field(default_factory=list)
    error: str = ""


@st.cache_resource
def _client():
    return WorkspaceClient()


def _result_frame(w, msg, attachment_id):
    resp = w.genie.get_message_attachment_query_result(
        SPACE_ID, msg.conversation_id, msg.message_id or msg.id, attachment_id)
    stmt = resp.statement_response
    if not stmt or not stmt.manifest or not stmt.result:
        return None
    cols = [c.name for c in stmt.manifest.schema.columns]
    df = pd.DataFrame(stmt.result.data_array or [], columns=cols)
    for c, meta in zip(cols, stmt.manifest.schema.columns):  # values arrive as strings
        kind = str(meta.type_name or "").upper()
        if any(t in kind for t in ("INT", "LONG", "SHORT", "BYTE", "DOUBLE", "FLOAT", "DECIMAL")):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        elif "DATE" in kind or "TIMESTAMP" in kind:
            df[c] = pd.to_datetime(df[c], errors="coerce")
            if (df[c].dropna().dt.normalize() == df[c].dropna()).all():
                df[c] = df[c].dt.date  # thread_month etc.: show 2025-01-01, not 2025-01-01 00:00:00
    return df


def ask(question: str, conversation_id: str | None = None) -> Answer:
    if not SPACE_ID:
        return Answer(error="GENIE_SPACE_ID is not set.")
    w = _client()
    try:
        if conversation_id:
            msg = w.genie.create_message_and_wait(SPACE_ID, conversation_id, question)
        else:
            msg = w.genie.start_conversation_and_wait(SPACE_ID, question)
    except Exception as e:  # network, permissions, timeout
        return Answer(conversation_id=conversation_id, error=str(e))

    ans = Answer(conversation_id=msg.conversation_id)
    if msg.error:
        ans.error = getattr(msg.error, "error", None) or str(msg.error)
    for a in msg.attachments or []:
        if a.text and a.text.content:
            ans.text += a.text.content
        if a.query:
            ans.sql = a.query.query or ""
            ans.description = a.query.description or ""
            try:
                ans.data = _result_frame(w, msg, a.attachment_id)
            except Exception as e:
                ans.error = f"Couldn't fetch the query result: {e}"
        if a.suggested_questions and a.suggested_questions.questions:
            ans.suggestions = list(a.suggested_questions.questions)
    if not (ans.text or ans.sql or ans.error):
        ans.error = f"Genie returned no answer (status {msg.status})."
    return ans
