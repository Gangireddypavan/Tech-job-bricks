import pandas as pd
import streamlit as st

from backend import GOLD, current_filters, query

f = current_filters()
where, params = f.where()

st.title("Explore posts")
st.caption(f"{f.months}. Search companies, role titles and skills. Showing up to 500 posts, newest first.")

search = st.text_input("Search", placeholder="e.g. Rust, Stripe, data engineer").strip().lower()

df = query(f"""
    SELECT j.thread_month, j.company,
           array_join(transform(j.roles, r -> r.title), ', ') AS roles,
           array_join(j.seniorities, ', ') AS seniority,
           j.remote_policy, array_join(j.countries, ', ') AS countries,
           j.salary_min, j.salary_max, j.salary_currency, j.salary_period, j.salary_mid_usd,
           array_join(j.skills, ', ') AS skills, j.hn_url
    FROM {GOLD}.jobs j
    WHERE {where}
      AND (:q = '' OR lower(j.company) LIKE :like
           OR exists(j.skills, s -> lower(s) LIKE :like)
           OR exists(j.roles, r -> lower(r.title) LIKE :like))
    ORDER BY j.thread_month DESC, j.company
    LIMIT 500""", params + (("q", search), ("like", f"%{search}%")))

st.caption(f"{len(df):,} posts" + (" (limit reached, narrow the search)" if len(df) == 500 else ""))
if df.empty:
    st.stop()


def pay(row):
    lo, hi = row.salary_min, row.salary_max
    if pd.isna(lo) and pd.isna(hi):
        return ""
    if pd.isna(lo):
        rng = f"up to {hi:,.0f}"
    elif pd.isna(hi):
        rng = f"{lo:,.0f}+"
    else:
        rng = f"{lo:,.0f}" if lo == hi else f"{lo:,.0f}–{hi:,.0f}"
    return f"{rng} {row.salary_currency or ''}/{row.salary_period or 'year'}"


df["pay"] = df.apply(pay, axis=1)
st.dataframe(
    df[["thread_month", "company", "roles", "seniority", "remote_policy", "countries", "pay",
        "salary_mid_usd", "skills", "hn_url"]],
    hide_index=True, use_container_width=True, height=620,
    column_config={
        "thread_month": st.column_config.DateColumn("Month", format="MMM YYYY"),
        "company": "Company",
        "roles": st.column_config.TextColumn("Roles", width="medium"),
        "seniority": "Seniority",
        "remote_policy": "Remote",
        "countries": "Countries",
        "pay": "Pay (as stated)",
        "salary_mid_usd": st.column_config.NumberColumn("Mid (USD/yr)", format="localized"),
        "skills": st.column_config.TextColumn("Skills", width="medium"),
        "hn_url": st.column_config.LinkColumn("Post", display_text="open"),
    })
