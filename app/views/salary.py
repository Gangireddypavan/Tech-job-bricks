import plotly.express as px
import streamlit as st

from backend import GOLD, country_name, current_filters, query
from theme import SENIORITY_ORDER, SERIES, range_chart, style

f = current_filters()
where, params = f.where()
paid = f"{where} AND j.salary_mid_usd IS NOT NULL"

st.title("Salaries")
st.caption(f"{f.months}. Only posts that state pay. Figures are the midpoint of each post's range, "
           "converted to annual USD at fixed reference exchange rates.")

QUANTILES = "percentile_approx(j.salary_mid_usd, array(0.25, 0.5, 0.75)) AS q, count(DISTINCT j.comment_id) AS n"


def with_quantiles(df):
    df[["p25", "p50", "p75"]] = df.q.tolist()
    return df.drop(columns="q")


kpi = query(f"SELECT {QUANTILES} FROM {GOLD}.jobs j WHERE {paid}", params)
if not kpi.n[0]:
    st.info("No posts with a stated salary match these filters.")
    st.stop()
kpi = with_quantiles(kpi).iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Posts stating pay", f"{int(kpi.n):,}")
c2.metric("Median (USD/yr)", f"${kpi.p50:,.0f}")
# One "$" only: Streamlit renders text between two dollar signs as LaTeX.
c3.metric("Middle 50% (USD/yr)", f"{kpi.p25 / 1000:,.0f}k – {kpi.p75 / 1000:,.0f}k")

min_n = st.slider("Hide groups with fewer posts than", 3, 50, 10)

left, right = st.columns(2)

# By seniority ---------------------------------------------------------------
# One row per (post, level): a post advertising three senior roles is still one senior salary.
sen = with_quantiles(query(f"""
    SELECT r.seniority, {QUANTILES}
    FROM (SELECT DISTINCT comment_id, seniority FROM {GOLD}.post_roles) r
    JOIN {GOLD}.jobs j ON j.comment_id = r.comment_id
    WHERE {paid} GROUP BY 1""", params))
sen = sen[sen.n >= min_n]
sen["order"] = sen.seniority.map(SENIORITY_ORDER.index)
with left:
    st.subheader("By seniority")
    st.caption("Each post counts once per level it advertises; a post with one pay range "
               "for several levels counts toward each of them.")
    if sen.empty:
        st.info("Not enough posts.")
    else:
        st.plotly_chart(range_chart(sen.sort_values("order"), "seniority"), use_container_width=True)

# By remote policy -----------------------------------------------------------
rem = with_quantiles(query(f"""
    SELECT j.remote_policy, {QUANTILES} FROM {GOLD}.jobs j WHERE {paid} GROUP BY 1""", params))
rem = rem[rem.n >= min_n].sort_values("p50", ascending=False)
with right:
    st.subheader("By remote policy")
    st.caption("Dot is the median; the band covers the middle 50% of posts.")
    if rem.empty:
        st.info("Not enough posts.")
    else:
        st.plotly_chart(range_chart(rem, "remote_policy"), use_container_width=True)

# By skill -------------------------------------------------------------------
skills = with_quantiles(query(f"""
    SELECT s.skill, {QUANTILES}
    FROM {GOLD}.post_skills s JOIN {GOLD}.jobs j ON j.comment_id = s.comment_id
    WHERE {paid} GROUP BY 1 ORDER BY n DESC LIMIT 20""", params))
skills = skills[skills.n >= min_n].sort_values("p50", ascending=False)
st.subheader("By skill (20 most common among posts with pay)")
if skills.empty:
    st.info("Not enough posts.")
else:
    st.plotly_chart(range_chart(skills, "skill"), use_container_width=True)

left, right = st.columns(2)

# By country -----------------------------------------------------------------
countries = with_quantiles(query(f"""
    SELECT c.country_code, {QUANTILES}
    FROM {GOLD}.post_countries c JOIN {GOLD}.jobs j ON j.comment_id = c.comment_id
    WHERE {paid} GROUP BY 1 ORDER BY n DESC LIMIT 12""", params))
countries = countries[countries.n >= min_n].sort_values("p50", ascending=False)
countries["country"] = countries.country_code.map(country_name)
with left:
    st.subheader("By country")
    if countries.empty:
        st.info("Not enough posts.")
    else:
        st.plotly_chart(range_chart(countries, "country"), use_container_width=True)

# Trend ------------------------------------------------------------------------
trend = with_quantiles(query(f"""
    SELECT j.thread_month, {QUANTILES} FROM {GOLD}.jobs j WHERE {paid} GROUP BY 1 ORDER BY 1""", params))
trend = trend[trend.n >= min_n]
with right:
    st.subheader("Median over time")
    if trend.empty:
        st.info("Not enough posts.")
    else:
        fig = px.line(trend, x="thread_month", y="p50", markers=True, custom_data=["n"],
                      color_discrete_sequence=[SERIES[0]])
        fig.update_traces(hovertemplate="%{x|%b %Y}: $%{y:,.0f} (n=%{customdata[0]})<extra></extra>")
        fig.update_yaxes(rangemode="tozero")  # a cropped axis makes small wobbles look dramatic
        st.plotly_chart(style(fig, legend=False, money_y=True), use_container_width=True)
