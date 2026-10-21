import plotly.express as px
import streamlit as st

from backend import GOLD, current_filters, query
from theme import REMOTE_COLORS, REMOTE_ORDER, SENIORITY_COLORS, SENIORITY_ORDER, SERIES, style

f = current_filters()
where, params = f.where()

st.title("Tech job market on Hacker News")
st.caption(f"Monthly \"Ask HN: Who is hiring?\" threads · {f.months}. "
           "Fields extracted from each post with an LLM (gpt-oss-120b).")

kpi = query(f"""
    SELECT count(*) AS posts,
           count(DISTINCT lower(company)) AS companies,
           avg(CASE WHEN remote_policy = 'remote' THEN 1.0 ELSE 0 END) AS remote_share,
           avg(CASE WHEN salary_mid_usd IS NOT NULL THEN 1.0 ELSE 0 END) AS salary_share,
           percentile_approx(salary_mid_usd, 0.5) AS median_salary
    FROM {GOLD}.jobs j WHERE {where}""", params).iloc[0]

if not kpi.posts:
    st.info("No job posts match these filters.")
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Job posts", f"{kpi.posts:,}")
c2.metric("Companies", f"{kpi.companies:,}")
c3.metric("Fully remote possible", f"{kpi.remote_share:.0%}")
c4.metric("Posts stating pay", f"{kpi.salary_share:.0%}")
c5.metric("Median salary (USD/yr)", f"${kpi.median_salary:,.0f}" if kpi.median_salary else "–")

# Posts per month ------------------------------------------------------------
monthly = query(f"""
    SELECT thread_month, count(*) AS posts FROM {GOLD}.jobs j
    WHERE {where} GROUP BY 1 ORDER BY 1""", params)
fig = px.line(monthly, x="thread_month", y="posts", markers=True,
              color_discrete_sequence=[SERIES[0]])
fig.update_traces(hovertemplate="%{x|%b %Y}: %{y:,} posts<extra></extra>")
st.subheader("Job posts per month")
st.caption("A rough hiring-demand signal: how many companies posted in each monthly thread.")
st.plotly_chart(style(fig, legend=False), use_container_width=True)

left, right = st.columns(2)

# Remote policy mix ----------------------------------------------------------
remote = query(f"""
    SELECT thread_month, remote_policy, count(*) AS posts FROM {GOLD}.jobs j
    WHERE {where} GROUP BY 1, 2""", params)
remote["share"] = remote.posts / remote.groupby("thread_month").posts.transform("sum")
fig = px.bar(remote, x="thread_month", y="share", color="remote_policy",
             color_discrete_map=REMOTE_COLORS, category_orders={"remote_policy": REMOTE_ORDER},
             custom_data=["posts"])
fig.update_traces(hovertemplate="%{x|%b %Y} · %{fullData.name}: %{y:.0%} (%{customdata[0]} posts)<extra></extra>")
fig.update_layout(barmode="stack", bargap=0.15)
with left:
    st.subheader("Remote, hybrid or on-site")
    st.caption("Share of each month's posts. \"Remote\" means fully remote work is offered.")
    st.plotly_chart(style(fig, percent_y=True), use_container_width=True)

# Seniority mix --------------------------------------------------------------
sen = query(f"""
    SELECT j.thread_month, r.seniority, count(*) AS roles
    FROM {GOLD}.post_roles r JOIN {GOLD}.jobs j ON j.comment_id = r.comment_id
    WHERE {where} GROUP BY 1, 2""", params)
sen["share"] = sen.roles / sen.groupby("thread_month").roles.transform("sum")
fig = px.bar(sen, x="thread_month", y="share", color="seniority",
             color_discrete_map=SENIORITY_COLORS, category_orders={"seniority": SENIORITY_ORDER},
             custom_data=["roles"])
fig.update_traces(hovertemplate="%{x|%b %Y} · %{fullData.name}: %{y:.0%} (%{customdata[0]} roles)<extra></extra>")
fig.update_layout(barmode="stack", bargap=0.15)
with right:
    st.subheader("Seniority of roles")
    st.caption("Share of advertised roles by level. \"Unspecified\" means the post states no level.")
    st.plotly_chart(style(fig, percent_y=True), use_container_width=True)
