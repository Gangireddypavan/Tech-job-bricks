import numpy as np
import plotly.express as px
import streamlit as st

from backend import GOLD, country_alpha3, country_name, current_filters, query
from theme import SEQUENTIAL, style

f = current_filters()
where, params = f.where()

st.title("Where the jobs are")
st.caption(f"{f.months}. A post counts for every country its roles can be done from (offices "
           "and countries named for remote work). Posts open to a whole region, such as "
           "\"Remote (EU)\" or \"Worldwide\", have no country and aren't shown here.")

df = query(f"""
    SELECT c.country_code,
           count(DISTINCT j.comment_id) AS posts,
           avg(CASE WHEN j.remote_policy = 'remote' THEN 1.0 ELSE 0 END) AS remote_share,
           percentile_approx(j.salary_mid_usd, 0.5) AS median_salary,
           count(j.salary_mid_usd) AS salary_posts
    FROM {GOLD}.post_countries c JOIN {GOLD}.jobs j ON j.comment_id = c.comment_id
    WHERE {where} GROUP BY 1 ORDER BY posts DESC""", params)
if df.empty:
    st.info("No posts with a country match these filters.")
    st.stop()

df["country"] = df.country_code.map(country_name)
df["iso3"] = df.country_code.map(country_alpha3)
# Log color scale: the US has several times more posts than any other country, and a linear
# scale would wash everything else out to the lightest step.
df["log_posts"] = np.log10(df.posts)
ticks = [t for t in (1, 10, 100, 1000, 10000) if t <= df.posts.max() * 1.5]

fig = px.choropleth(df.dropna(subset=["iso3"]), locations="iso3", color="log_posts",
                    hover_name="country", custom_data=["posts"],
                    color_continuous_scale=SEQUENTIAL)
fig.update_traces(hovertemplate="%{hovertext}: %{customdata[0]:,} posts<extra></extra>",
                  marker_line_color="#fcfcfb", marker_line_width=0.5)
fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth",
                projection_rotation=dict(lon=0), lataxis_range=[-58, 85],
                bgcolor="#fcfcfb", landcolor="#f0efec", showland=True)
fig.update_layout(coloraxis_colorbar=dict(title="Posts", thickness=12,
                                          tickvals=np.log10(ticks), ticktext=[f"{t:,}" for t in ticks]))
# Maps scroll-zoom by default, which traps the mouse wheel when scrolling past the map.
st.plotly_chart(style(fig, height=460, legend=False), use_container_width=True,
                config={"scrollZoom": False})

st.subheader("By country")
table = df[["country", "country_code", "posts", "remote_share", "median_salary", "salary_posts"]].copy()
table["remote_share"] *= 100
st.dataframe(
    table, hide_index=True, use_container_width=True,
    column_config={
        "country": "Country",
        "country_code": "Code",
        "posts": st.column_config.NumberColumn("Job posts", format="%d"),
        "remote_share": st.column_config.NumberColumn("Fully remote possible", format="%.0f%%"),
        "median_salary": st.column_config.NumberColumn("Median salary (USD/yr)", format="localized"),
        "salary_posts": st.column_config.NumberColumn("Posts stating pay", format="%d"),
    })
