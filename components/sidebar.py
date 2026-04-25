from __future__ import annotations

from pathlib import Path

import streamlit as st


NAV_MAP = {
    "dashboard": "\U0001F3E0 Dashboard",
    "profile": "\U0001F464 Profile Setup",
    "ingest": "\U0001F4E5 Ingest Jobs",
    "url_validation": "\U0001F9EA URL Validation",
    "run_history": "\U0001F4DD Run History",
    "score": "\U0001F3AF Score Jobs",
    "pipeline": "\U0001F4CB Pipeline",
    "analytics": "\U0001F4CA Analytics",
    "howto": "\u2753 How To Use",
    "settings": "\u2699\ufe0f Settings",
}


def render_sidebar(db_path: str, active_profile: str | None, db_exists: bool) -> str:
    with st.sidebar:
        st.markdown('<div class="pc-sidebar-title">PM Copilot</div>', unsafe_allow_html=True)
        st.markdown('<div class="pc-sidebar-sub">Product job search operating system</div>', unsafe_allow_html=True)

        db_state = "Connected" if db_exists else "Missing"
        st.caption(f"Database: {db_state}")
        st.caption(f"Active profile: {active_profile or 'Not set'}")

        nav_keys = list(NAV_MAP.keys())
        page = st.radio(
            "Navigate",
            options=nav_keys,
            format_func=lambda key: NAV_MAP[key],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown(
            f"""
            <div class="pc-side-card">
              <div class="pc-side-label">DB Path</div>
              <div class="pc-dbpath">{Path(db_path)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        last_action = str(st.session_state.get("last_action_name", "")).strip()
        last_action_time = str(st.session_state.get("last_action_time", "")).strip()
        if last_action:
            st.markdown(
                f"""
                <div class="pc-side-card">
                  <div class="pc-side-label">Last Action</div>
                  <div class="pc-action-pill">&#10003; {last_action}</div>
                  <div class="pc-action-time">{last_action_time}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.caption("Tip: Start with Profile Setup, then ingest and score jobs.")

    return page
