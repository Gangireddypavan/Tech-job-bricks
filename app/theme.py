"""Chart styling: the reference data-viz palette and Plotly helpers.

Categorical hues are assigned in a fixed order and follow the entity (remote policy,
seniority, skill), never its rank. "unspecified" is always muted gray, not a series hue.
"""

import plotly.graph_objects as go

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
UP, DOWN = "#2a78d6", "#e34948"          # diverging poles
RANGE_FILL = "#b7d3f6"                   # IQR band behind a median marker

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

REMOTE_ORDER = ["remote", "hybrid", "onsite", "unspecified"]
REMOTE_COLORS = {"remote": SERIES[0], "hybrid": SERIES[1], "onsite": SERIES[2], "unspecified": MUTED}

SENIORITY_ORDER = ["intern", "junior", "mid", "senior", "staff+", "lead", "manager", "unspecified"]
SENIORITY_COLORS = {s: SERIES[i] for i, s in enumerate(SENIORITY_ORDER[:-1])} | {"unspecified": MUTED}


def style(fig, height=340, legend=True, percent_y=False, money_x=False, money_y=False):
    fig.update_layout(
        template="none", height=height, margin=dict(l=8, r=16, t=40 if legend else 12, b=8),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK2, size=13),
        hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=FONT, color=INK)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, font=dict(color=INK2)),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickcolor=AXIS, ticks="outside",
                     zeroline=False, title=None, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, title=None,
                     tickfont=dict(color=MUTED))
    fig.update_traces(selector=dict(type="scatter", mode="lines"), line=dict(width=2))
    fig.update_traces(selector=dict(type="scatter", mode="lines+markers"), line=dict(width=2),
                      marker=dict(size=8, line=dict(color=SURFACE, width=2)))
    fig.update_traces(selector=dict(type="bar"), marker_line=dict(color=SURFACE, width=2))
    if fig.layout.barmode in ("stack", "relative"):
        # Plotly Express gives each color its own offsetgroup; newer plotly.js (bundled with
        # Streamlit) then draws stacked bars side by side. One shared group = a real stack.
        for t in fig.data:
            if t.type == "bar":
                t.offsetgroup = None
    if percent_y:
        fig.update_yaxes(tickformat=".0%")
    if money_x:
        fig.update_xaxes(tickprefix="$", tickformat="~s")
    if money_y:
        fig.update_yaxes(tickprefix="$", tickformat="~s")
    return fig


def range_chart(df, label_col, height=None):
    """Horizontal IQR band (p25-p75) with a median dot per row: salary distributions from
    precomputed quantiles. df needs columns label_col, p25, p50, p75, n."""
    labels = [f"{l}  (n={n:,})" for l, n in zip(df[label_col], df["n"])]
    fig = go.Figure()
    fig.add_bar(y=labels, x=df["p75"] - df["p25"], base=df["p25"], orientation="h",
                marker=dict(color=RANGE_FILL, cornerradius=4), name="Middle 50%",
                customdata=df[["p25", "p75"]].to_numpy(),
                hovertemplate="%{y}<br>middle 50%: $%{customdata[0]:,.0f} – $%{customdata[1]:,.0f}<extra></extra>")
    fig.add_scatter(y=labels, x=df["p50"], mode="markers", name="Median",
                    marker=dict(color=SERIES[0], size=11, line=dict(color=SURFACE, width=2)),
                    hovertemplate="%{y}<br>median $%{x:,.0f}<extra></extra>")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    return style(fig, height=height or max(220, 34 * len(df) + 60), money_x=True)
