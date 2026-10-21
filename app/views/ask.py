from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from genie_client import ask
from theme import SERIES, style

st.title("Ask a question")
st.caption("Ask about skills, salaries, seniority, remote work or countries in plain English. "
           "Genie writes SQL over the job-post tables and answers. Check the SQL to see exactly what was counted.")

SAMPLES = [
    "What are the fastest-growing skills this year?",
    "What share of jobs are fully remote, by month?",
    "What is the median salary for senior engineers in the US?",
    "Which companies post the most often?",
    "How many jobs mention Rust each month?",
]

history = st.session_state.setdefault("ask_history", [])


def auto_chart(df: pd.DataFrame):
    """A simple chart when the result is one dimension plus one number; otherwise nothing."""
    if df is None or df.empty or len(df.columns) < 2 or len(df) < 2:
        return None
    x, y = df.columns[0], df.columns[-1]
    if not pd.api.types.is_numeric_dtype(df[y]):
        return None
    is_time = pd.api.types.is_datetime64_any_dtype(df[x]) or (
        df[x].dtype == object and df[x].map(lambda v: isinstance(v, date)).all())
    if is_time:
        fig = px.line(df, x=x, y=y, markers=True, color_discrete_sequence=[SERIES[0]])
        fig.update_yaxes(rangemode="tozero")
    elif len(df) <= 30:
        fig = px.bar(df, x=y, y=x, orientation="h", color_discrete_sequence=[SERIES[0]])
        fig.update_traces(marker_cornerradius=4)
        fig.update_yaxes(autorange="reversed", type="category")
    else:
        return None
    return style(fig, height=min(480, 28 * len(df) + 80), legend=False)


def render(turn):
    with st.chat_message("user"):
        st.write(turn["question"])
    ans = turn["answer"]
    with st.chat_message("assistant"):
        if ans.error:
            st.error(ans.error)
        if ans.text:
            st.markdown(ans.text)
        if ans.data is not None and not ans.data.empty:
            fig = auto_chart(ans.data)
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(ans.data, hide_index=True, use_container_width=True)
        if ans.sql:
            with st.expander("SQL Genie ran" + (f": {ans.description}" if ans.description else "")):
                st.code(ans.sql, language="sql")


for turn in history:
    render(turn)

question = st.chat_input("e.g. Which skills pay the most for remote roles?")
if not history and not question:
    st.write("Try one of these:")
    for i, q in enumerate(SAMPLES):
        if st.button(q, key=f"sample{i}"):
            question = q

last = history[-1]["answer"] if history else None
if last and last.suggestions and not question:
    st.write("Follow-up ideas:")
    for i, q in enumerate(last.suggestions[:3]):
        if st.button(q, key=f"suggest{len(history)}_{i}"):
            question = q

if question:
    conversation = history[-1]["answer"].conversation_id if history else None
    with st.spinner("Genie is writing and running SQL…"):
        answer = ask(question, conversation)
    history.append({"question": question, "answer": answer})
    st.rerun()

if history and st.button("New conversation", type="tertiary"):
    history.clear()
    st.rerun()
