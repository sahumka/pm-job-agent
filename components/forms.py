from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.actions import action_button, action_submit_button
from components.cards import render_chip_row
from src.dashboard_utils import split_csv_string, suggest_keywords_from_sample_jds


PROFILE_TEMPLATE = {
    "user_id": "",
    "display_name": "",
    "notification_email": "",
    "years_experience": 0,
    "target_seniority": ["mid", "senior"],
    "work_modes": ["remote", "hybrid"],
    "visa_requirements": [],
    "compensation_min_usd": 0,
    "target_roles": [],
    "preferred_locations": [],
    "excluded_locations": [],
    "domains": [],
    "skills": [],
    "must_have_keywords": [],
    "nice_to_have_keywords": [],
    "avoid_keywords": [],
}


def _csv_default(values: list[str]) -> str:
    return ", ".join(values)


def render_profile_form(base: dict[str, Any], key_prefix: str = "profile") -> tuple[bool, dict[str, Any], list[str]]:
    data = dict(PROFILE_TEMPLATE)
    data.update(base or {})

    with st.form(f"{key_prefix}_form"):
        st.markdown("### Basic Info")
        st.caption("Who is this profile for, and what experience level should scoring assume?")
        c1, c2 = st.columns(2)
        with c1:
            user_id = st.text_input("User ID", value=str(data.get("user_id", "")), placeholder="tanya_product")
            display_name = st.text_input("Display Name", value=str(data.get("display_name", "")), placeholder="Tanya - Product")
            notification_email = st.text_input(
                "Notification email",
                value=str(data.get("notification_email", "")),
                placeholder="name@example.com",
            )
            years_experience = st.number_input(
                "Years of experience", min_value=0, max_value=50, value=int(data.get("years_experience", 0) or 0)
            )
        with c2:
            target_seniority = st.multiselect(
                "Target seniority",
                options=["entry", "mid", "senior", "principal"],
                default=[str(x) for x in data.get("target_seniority", ["mid", "senior"])],
            )
            work_modes = st.multiselect(
                "Work modes",
                options=["remote", "hybrid", "onsite"],
                default=[str(x) for x in data.get("work_modes", ["remote", "hybrid"])],
            )

        st.markdown("### Target Roles")
        st.caption("Define role titles and location preferences to drive filtering and scoring.")
        target_roles = st.text_input("Target roles", value=_csv_default([str(x) for x in data.get("target_roles", [])]))
        preferred_locations = st.text_input(
            "Preferred locations", value=_csv_default([str(x) for x in data.get("preferred_locations", [])])
        )
        excluded_locations = st.text_input(
            "Excluded locations", value=_csv_default([str(x) for x in data.get("excluded_locations", [])])
        )

        st.markdown("### Visa & Compensation")
        st.caption("Capture sponsorship and minimum-comp expectations.")
        visa_requirements = st.text_input(
            "Visa/sponsorship needs",
            value=_csv_default([str(x) for x in data.get("visa_requirements", [])]),
            placeholder="h1b, sponsorship",
        )
        compensation_min_usd = st.number_input(
            "Minimum compensation (USD)", min_value=0, value=int(data.get("compensation_min_usd", 0) or 0), step=5000
        )

        st.markdown("### Skills & Keywords")
        st.caption("These keywords influence fit scoring and tailoring hints.")
        domains = st.text_input("Domains", value=_csv_default([str(x) for x in data.get("domains", [])]))
        skills = st.text_input("Skills", value=_csv_default([str(x) for x in data.get("skills", [])]))
        must_have_keywords = st.text_input(
            "Must-have keywords", value=_csv_default([str(x) for x in data.get("must_have_keywords", [])])
        )
        nice_to_have_keywords = st.text_input(
            "Nice-to-have keywords", value=_csv_default([str(x) for x in data.get("nice_to_have_keywords", [])])
        )
        avoid_keywords = st.text_input("Avoid keywords", value=_csv_default([str(x) for x in data.get("avoid_keywords", [])]))

        submitted = action_submit_button("Save Profile", action_name="Save Profile", use_container_width=True)

    profile = {
        "user_id": user_id.strip(),
        "display_name": display_name.strip() or user_id.strip(),
        "notification_email": notification_email.strip(),
        "years_experience": int(years_experience),
        "target_seniority": target_seniority or ["mid", "senior"],
        "work_modes": work_modes or ["remote", "hybrid", "onsite"],
        "visa_requirements": split_csv_string(visa_requirements),
        "compensation_min_usd": int(compensation_min_usd),
        "target_roles": split_csv_string(target_roles),
        "preferred_locations": split_csv_string(preferred_locations),
        "excluded_locations": split_csv_string(excluded_locations),
        "domains": split_csv_string(domains),
        "skills": split_csv_string(skills),
        "must_have_keywords": split_csv_string(must_have_keywords),
        "nice_to_have_keywords": split_csv_string(nice_to_have_keywords),
        "avoid_keywords": split_csv_string(avoid_keywords),
    }

    return submitted, profile, profile["skills"]


def render_keyword_assistant() -> list[str]:
    st.markdown("### Keyword Assistant")
    st.caption("Paste 1-5 job descriptions and I'll suggest recurring PM keywords.")

    text = st.text_area(
        "Sample job descriptions",
        height=220,
        placeholder="Paste role snippets here (product strategy, roadmapping, experimentation, stakeholder alignment...)",
        label_visibility="collapsed",
    )

    suggestions: list[str] = st.session_state.get("kw_suggestions", [])
    if action_button("Suggest Keywords", action_name="Suggest Keywords", use_container_width=True):
        raw = suggest_keywords_from_sample_jds(text, top_n=28)
        # Keep stable order while removing duplicates and blank tokens.
        deduped: list[str] = []
        seen: set[str] = set()
        for item in raw:
            token = str(item).strip()
            key = token.lower()
            if not token or key in seen:
                continue
            seen.add(key)
            deduped.append(token)
        suggestions = deduped
        st.session_state["kw_suggestions"] = suggestions

    if suggestions:
        st.markdown("**Suggested Keywords**")
        render_chip_row(suggestions)

        selected_defaults = st.session_state.get("kw_selected", [])
        table_rows = [{"select": kw in selected_defaults, "keyword": kw} for kw in suggestions]
        edited = st.data_editor(
            pd.DataFrame(table_rows),
            key="kw_picker_editor",
            hide_index=True,
            use_container_width=True,
            column_config={
                "select": st.column_config.CheckboxColumn("Add", help="Select keywords to add to profile"),
                "keyword": st.column_config.TextColumn("Keyword", disabled=True),
            },
            num_rows="fixed",
        )
        selected = [str(row["keyword"]) for _, row in edited.iterrows() if bool(row.get("select", False))]
        st.session_state["kw_selected"] = selected

        if selected:
            st.caption(f"{len(selected)} keyword(s) selected")
        else:
            st.caption("Select keywords from the table above.")
        return selected

    st.caption("No suggestions yet.")
    return []
