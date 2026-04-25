from __future__ import annotations

from typing import Any

import streamlit as st

from components.empty_states import render_empty_state


def render_jobs_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        render_empty_state("No jobs yet", "Ingest jobs to populate your pipeline table.", kind="blank")
        return

    table_rows = []
    for row in rows:
        table_rows.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "company": row.get("company"),
                "location": row.get("location"),
                "status": row.get("status"),
                "fit_score": row.get("fit_score"),
                "job_board": row.get("job_board"),
                "date_found": row.get("date_found"),
                "follow_up_date": row.get("follow_up_date"),
                "source_url": row.get("source_url"),
            }
        )

    st.dataframe(table_rows, use_container_width=True, hide_index=True)


def render_recent_activity(rows: list[dict[str, Any]], max_rows: int = 12) -> None:
    if not rows:
        render_empty_state("No recent activity", "Changes and updates will appear here.", kind="search")
        return

    st.dataframe(
        [
            {
                "date": row.get("updated_at") or row.get("created_at"),
                "job": f"{row.get('title')} @ {row.get('company')}",
                "status": row.get("status"),
                "score": row.get("fit_score"),
            }
            for row in rows[:max_rows]
        ],
        use_container_width=True,
        hide_index=True,
    )
