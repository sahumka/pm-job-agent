from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

import streamlit as st

from components.empty_states import render_empty_state

try:
    import plotly.express as px
except Exception:  # pragma: no cover - graceful fallback when plotly isn't installed yet
    px = None  # type: ignore[assignment]


def _date_to_week(value: str | None) -> str:
    if not value:
        return "Unknown"
    raw = str(value).split(" ", 1)[0].split("T", 1)[0]
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return "Unknown"
    return f"{dt.year}-W{dt.isocalendar().week:02d}"


def render_analytics_charts(rows: list[dict[str, Any]]) -> None:
    if px is None:
        st.warning("Plotly is not installed. Install dependencies to enable analytics charts: `pip install -r requirements.txt`")
        return
    if not rows:
        render_empty_state("No analytics data", "Run ingestion and scoring to unlock insights.", kind="search")
        return

    scores = [float(r.get("fit_score", 0) or 0) for r in rows if r.get("fit_score") is not None]
    sources = Counter(str(r.get("job_board", "unknown")) for r in rows)
    statuses = Counter(str(r.get("status", "New")) for r in rows)
    companies = Counter(str(r.get("company", "Unknown")) for r in rows)
    weeks = Counter(_date_to_week(str(r.get("date_found", ""))) for r in rows)

    c1, c2 = st.columns(2)
    with c1:
        fig_sources = px.pie(
            names=list(sources.keys()),
            values=list(sources.values()),
            title="Job Sources",
            color_discrete_sequence=["#0A66C2", "#16A34A", "#F59E0B", "#FF5A5F", "#64748B"],
            hole=0.45,
        )
        fig_sources.update_layout(paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig_sources, use_container_width=True)

    with c2:
        fig_status = px.bar(
            x=list(statuses.keys()),
            y=list(statuses.values()),
            title="Application Status Funnel",
            color=list(statuses.keys()),
            color_discrete_sequence=["#0A66C2", "#16A34A", "#F59E0B", "#FF5A5F", "#64748B"],
        )
        fig_status.update_layout(showlegend=False, paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig_status, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        if scores:
            fig_scores = px.histogram(
                x=scores,
                nbins=12,
                title="Fit Score Distribution",
                color_discrete_sequence=["#0A66C2"],
            )
            fig_scores.update_layout(paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig_scores, use_container_width=True)
        else:
            render_empty_state("No scores yet", "Score more jobs to view distribution analytics.", kind="blank")

    with c4:
        top_companies = companies.most_common(10)
        fig_companies = px.bar(
            x=[x[1] for x in top_companies],
            y=[x[0] for x in top_companies],
            orientation="h",
            title="Top Companies Applied/Tracked",
            color_discrete_sequence=["#0A66C2"],
        )
        fig_companies.update_layout(showlegend=False, paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig_companies, use_container_width=True)

    fig_week = px.line(
        x=list(weeks.keys()),
        y=list(weeks.values()),
        markers=True,
        title="Applications / Jobs by Week",
        color_discrete_sequence=["#0A66C2"],
    )
    fig_week.update_layout(paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=45, b=10))
    st.plotly_chart(fig_week, use_container_width=True)
