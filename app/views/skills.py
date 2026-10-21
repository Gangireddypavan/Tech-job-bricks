import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend import GOLD, current_filters, query
from theme import DOWN, SERIES, UP, style

f = current_filters()
where, params = f.where()

st.title("Skills in demand")
st.caption(f"{f.months}. A skill counts once per post; shares are of all job posts matching the filters.")

base = f"WITH f AS (SELECT comment_id, thread_month FROM {GOLD}.jobs j WHERE {where})"

# Top skills -------------------------------------------------------------------
top = query(f"""{base}
    SELECT s.skill, count(*) AS posts, count(*) / (SELECT count(*) FROM f) AS share
    FROM {GOLD}.post_skills s JOIN f ON f.comment_id = s.comment_id
    GROUP BY s.skill ORDER BY posts DESC, s.skill LIMIT 25""", params)
if top.empty:
    st.info("No skills extracted for posts matching these filters yet.")
    st.stop()

fig = px.bar(top, x="share", y="skill", orientation="h", color_discrete_sequence=[SERIES[0]],
             custom_data=["posts"], text=top.share.map("{:.0%}".format))
fig.update_traces(marker_cornerradius=4, textposition="outside", cliponaxis=False,
                  textfont=dict(size=12),
                  hovertemplate="%{y}: %{x:.1%} of posts (%{customdata[0]:,})<extra></extra>")
fig.update_yaxes(autorange="reversed")
fig.update_xaxes(showticklabels=False, showgrid=False)
st.subheader("Top 25 skills")
st.plotly_chart(style(fig, height=26 * len(top) + 40, legend=False), use_container_width=True)

# Trend for chosen skills ---------------------------------------------------
st.subheader("Trend over time")
choices = st.multiselect("Skills to compare (up to 6)", top.skill.tolist(),
                         default=top.skill.head(4).tolist(), max_selections=6)

# Colors follow the skill, not its position: a skill keeps its hue while others come and go.
palette = st.session_state.setdefault("skill_colors", {})
for gone in set(palette) - set(choices):
    del palette[gone]
for skill in choices:
    if skill not in palette:
        palette[skill] = next(c for c in SERIES if c not in palette.values())

if choices:
    names = [f"k{i}" for i in range(len(choices))]
    trend = query(f"""{base},
        totals AS (SELECT thread_month, count(*) AS n FROM f GROUP BY 1)
        SELECT t.thread_month, s.skill, count(*) / max(t.n) AS share
        FROM f JOIN {GOLD}.post_skills s ON s.comment_id = f.comment_id
        JOIN totals t ON t.thread_month = f.thread_month
        WHERE s.skill IN ({', '.join(':' + n for n in names)})
        GROUP BY 1, 2""", params + tuple(zip(names, choices)))
    months = query(f"SELECT DISTINCT thread_month FROM {GOLD}.jobs j WHERE {where}", params).thread_month
    grid = pd.MultiIndex.from_product([sorted(months), choices], names=["thread_month", "skill"])
    trend = trend.set_index(["thread_month", "skill"]).reindex(grid, fill_value=0).reset_index()
    fig = px.line(trend, x="thread_month", y="share", color="skill", markers=True,
                  color_discrete_map=palette, category_orders={"skill": choices})
    fig.update_traces(hovertemplate="%{fullData.name}: %{y:.1%}<extra></extra>")
    fig.update_layout(hovermode="x unified")
    st.caption("Share of each month's posts that mention the skill.")
    st.plotly_chart(style(fig, percent_y=True), use_container_width=True)

# Fastest growing ----------------------------------------------------------------
st.subheader("Fastest growing and declining")
all_months = sorted(query(f"SELECT DISTINCT thread_month FROM {GOLD}.jobs j WHERE {where}",
                          params).thread_month)
window = min(6, len(all_months) // 2)
if window < 1:
    st.info("Select at least two months to compare.")
    st.stop()
early_end, late_start = all_months[window - 1], all_months[-window]
min_posts = st.slider("Minimum posts mentioning a skill (both periods combined)", 5, 100, 20, step=5)
growth = query(f"""{base},
    p AS (SELECT comment_id, CASE WHEN thread_month <= :early_end THEN 'early'
                                  WHEN thread_month >= :late_start THEN 'late' END AS period FROM f),
    totals AS (SELECT count_if(period = 'early') AS early_n, count_if(period = 'late') AS late_n FROM p)
    SELECT s.skill,
           count_if(p.period = 'early') AS early_posts, count_if(p.period = 'late') AS late_posts,
           count_if(p.period = 'early') / max(t.early_n) AS early_share,
           count_if(p.period = 'late') / max(t.late_n) AS late_share
    FROM {GOLD}.post_skills s JOIN p ON p.comment_id = s.comment_id CROSS JOIN totals t
    WHERE p.period IS NOT NULL
    GROUP BY s.skill HAVING count(*) >= :min_posts""",
    params + (("early_end", early_end), ("late_start", late_start), ("min_posts", min_posts)))
st.caption(f"Share of posts in the first {window} months ({all_months[0]:%b %Y}–{early_end:%b %Y}) "
           f"vs the last {window} ({late_start:%b %Y}–{all_months[-1]:%b %Y}), in percentage points.")

if growth.empty:
    st.info("Not enough data for a comparison yet. Lower the minimum or widen the months.")
else:
    growth["change"] = growth.late_share - growth.early_share
    growth = growth.sort_values("change")
    movers = pd.concat([growth.head(8), growth.tail(8)]).drop_duplicates("skill")
    movers = movers[movers.change != 0]
    fig = go.Figure(go.Bar(
        x=movers.change * 100, y=movers.skill, orientation="h",
        marker=dict(color=[UP if c > 0 else DOWN for c in movers.change], cornerradius=4),
        customdata=movers[["early_share", "late_share", "early_posts", "late_posts"]].to_numpy(),
        hovertemplate="%{y}: %{customdata[0]:.1%} → %{customdata[1]:.1%} of posts"
                      "<br>(%{customdata[2]} → %{customdata[3]} posts)<extra></extra>"))
    fig.update_xaxes(ticksuffix=" pts", showgrid=True, gridcolor="#e1e0d9", zeroline=True,
                     zerolinecolor="#c3c2b7")
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(style(fig, height=26 * len(movers) + 60, legend=False), use_container_width=True)

    with st.expander("All skills in the comparison"):
        table = growth.sort_values("change", ascending=False).copy()
        table[["early_share", "late_share", "change"]] *= 100
        st.dataframe(
            table[["skill", "early_posts", "early_share", "late_posts", "late_share", "change"]],
            hide_index=True, use_container_width=True,
            column_config={
                "skill": "Skill",
                "early_posts": st.column_config.NumberColumn("Posts (early)"),
                "early_share": st.column_config.NumberColumn("Share (early)", format="%.1f%%"),
                "late_posts": st.column_config.NumberColumn("Posts (late)"),
                "late_share": st.column_config.NumberColumn("Share (late)", format="%.1f%%"),
                "change": st.column_config.NumberColumn("Change (pts)", format="%+.1f"),
            })
