from __future__ import annotations

import json
import shutil
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from components.actions import action_button
from components.cards import (
    render_chip_row,
    render_job_card,
    render_metric_card,
    render_page_header,
    render_status_badge,
)
from components.charts import render_analytics_charts
from components.empty_states import render_empty_state
from components.forms import render_keyword_assistant, render_profile_form
from components.sidebar import render_sidebar
from components.tables import render_jobs_table, render_recent_activity
from services.db import (
    get_crawl_enabled_profiles,
    dashboard_snapshot,
    delete_jobs_by_ids,
    ensure_db,
    get_active_profile,
    get_fetch_runs,
    get_jobs,
    get_profile_runtime_status,
    get_profiles,
    list_users,
    load_profile_data,
    save_job_update,
    save_profile_data,
    set_profile_runtime_active,
    set_active_profile,
    top_matching_roles,
)
from services.ingestion import ingest_single_job_url, run_job_ingestion
from services.scoring import missing_keywords, parse_keywords, score_band, sponsorship_signal
from src.dashboard_utils import follow_up_queue, funnel_metrics
from src.profile_sources import bootstrap_profile_sources, profile_source_dir
from src.resume_intake import save_base_resume
from src.runtime_config import env_str
from src.run_hourly import run_hourly
from src.validate_targets import run_validation
from styles.theme import apply_theme

ICON = {
    "dashboard": "\U0001F3E0",
    "profile": "\U0001F464",
    "ingest": "\U0001F4E5",
    "score": "\U0001F3AF",
    "pipeline": "\U0001F4CB",
    "analytics": "\U0001F4CA",
    "howto": "\u2753",
    "settings": "\u2699\ufe0f",
    "high_fit": "\u2B50",
    "interviews": "\U0001F4DE",
    "followups": "\u23F0",
    "interview_rate": "\U0001F9EA",
    "offer_rate": "\U0001F3C6",
    "apply_rate": "\U0001F4CD",
    "threshold": "\U0001F39A\ufe0f",
    "response_rate": "\U0001F4C8",
    "companies": "\U0001F3E2",
}

PIPELINE_COLUMNS: dict[str, list[str]] = {
    "Saved": ["Saved", "New", "Interested"],
    "Applied": ["Applied"],
    "Recruiter Screen": ["Recruiter Screen"],
    "Interview": ["Interview"],
    "Offer": ["Offer"],
    "Rejected / Archived": ["Rejected", "Archived", "Skip"],
}

PIPELINE_STATUSES = ["Saved", "Applied", "Recruiter Screen", "Interview", "Offer", "Rejected", "Archived", "Skip"]


def _init_state() -> None:
    if "db_path" not in st.session_state:
        st.session_state["db_path"] = env_str("DB_PATH", "data/jobs.db")
    if "last_ingest_summary" not in st.session_state:
        st.session_state["last_ingest_summary"] = None


def _resolve_user_filter() -> tuple[str | None, list[str]]:
    db_path = st.session_state["db_path"]
    users = sorted(set(get_profiles() + list_users(db_path)))
    active = get_active_profile()
    options = ["All"] + users
    default_idx = options.index(active) if active in options else 0
    choice = st.selectbox("Profile", options=options, index=default_idx)
    return (None if choice == "All" else choice), users


def _dashboard_page() -> None:
    cta = render_page_header(
        "PM Job Search Copilot",
        "Find, score, and track product roles with a structured application pipeline.",
        cta_label="Run Job Ingestion",
        cta_key="hero_run_ingestion",
        icon=ICON["dashboard"],
    )

    user_filter, _ = _resolve_user_filter()

    with st.container(border=True):
        if user_filter:
            runtime = get_profile_runtime_status(user_filter)
            status_text = "Active" if runtime.get("crawl_active") else "Inactive"
            configured_text = "Configured" if runtime.get("configured") else "Not Configured"
            c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
            with c1:
                render_metric_card("Crawl Status", status_text)
            with c2:
                render_metric_card("Profile Setup", configured_text)
            with c3:
                toggle_label = "Make Inactive" if runtime.get("crawl_active") else "Make Active"
                if action_button(toggle_label, action_name=f"Toggle Crawl Active {user_filter}", use_container_width=True):
                    ok = set_profile_runtime_active(user_filter, not bool(runtime.get("crawl_active")))
                    if ok:
                        st.success(f"{user_filter} crawl status updated.")
                        st.rerun()
                    else:
                        st.error("Could not update crawl status for this profile.")
        else:
            enabled = get_crawl_enabled_profiles()
            total_profiles = len(get_profiles())
            c1, c2 = st.columns(2)
            with c1:
                render_metric_card("Crawl-Active Profiles", str(len(enabled)))
            with c2:
                render_metric_card("Total Profiles", str(total_profiles))
            st.caption("Select a profile to toggle active/inactive crawl status.")

    rows = get_jobs(st.session_state["db_path"], user_id=user_filter, limit=2000)
    snap = dashboard_snapshot(rows)

    top_row = st.columns(3)
    with top_row[0]:
        render_metric_card("Jobs Ingested", str(snap["jobs_ingested"]), icon=ICON["ingest"])
    with top_row[1]:
        render_metric_card("Jobs Scored", str(snap["jobs_scored"]), icon=ICON["score"])
    with top_row[2]:
        render_metric_card("High-Fit Roles", str(snap["high_fit_roles"]), icon=ICON["high_fit"])

    st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)

    bottom_row = st.columns(3)
    with bottom_row[0]:
        render_metric_card("Applications", str(snap["applications_started"]), icon=ICON["pipeline"])
    with bottom_row[1]:
        render_metric_card("Interviews", str(snap["interviews"]), icon=ICON["interviews"])
    with bottom_row[2]:
        render_metric_card("Follow-ups Due", str(snap["follow_ups_due"]), icon=ICON["followups"])

    if cta:
        render_empty_state("Ready to ingest", "Go to Ingest Jobs to run the complete collection workflow.", kind="search")

    left, right = st.columns([1.15, 0.85])
    with left:
        st.markdown("### Recommended Next Actions")
        queue = follow_up_queue(rows)
        if queue:
            for item in queue[:6]:
                with st.container(border=True):
                    st.markdown(f"**{item.get('title', 'Role')}** at **{item.get('company', 'Company')}**")
                    st.caption(item.get("follow_up_reason", "Follow-up needed"))
        else:
            render_empty_state("No urgent follow-ups", "Great momentum. Focus on high-fit applications today.", kind="blank")

        st.markdown("### Top Matching Roles")
        for job in top_matching_roles(rows, limit=6):
            render_job_card(
                title=str(job.get("title", "Unknown")),
                company=str(job.get("company", "Unknown")),
                location=str(job.get("location", "Unknown")),
                fit_score=float(job.get("fit_score", 0) or 0),
                summary=str(job.get("score_reason", "No summary available."))[:180],
            )

    with right:
        st.markdown("### Pipeline Health")
        fm = funnel_metrics(rows)
        p1, p2, p3 = st.columns(3)
        with p1:
            render_metric_card("Apply Rate", f"{fm['apply_rate_pct']:.1f}%", icon=ICON["apply_rate"])
        with p2:
            render_metric_card("Interview Rate", f"{fm['interview_rate_from_applied_pct']:.1f}%", icon=ICON["interview_rate"])
        with p3:
            render_metric_card("Offer Rate", f"{fm['offer_rate_from_interview_pct']:.1f}%", icon=ICON["offer_rate"])

        st.markdown("### Recent Activity")
        render_recent_activity(rows, max_rows=10)

        st.markdown("### Automation Health")
        fetch_runs = get_fetch_runs(st.session_state["db_path"], profile_id=user_filter, limit=40)
        if not fetch_runs:
            st.caption("No hourly runs logged yet.")
        else:
            latest = fetch_runs[0]
            status_label = str(latest.get("status", "unknown")).strip().lower()
            status_display = "Healthy" if status_label == "success" else "Attention Needed"
            a1, a2 = st.columns(2)
            with a1:
                render_metric_card("Latest Run", status_display)
            with a2:
                render_metric_card("Latest Inserted", str(latest.get("jobs_inserted", 0)))

            success_count = sum(1 for r in fetch_runs if str(r.get("status", "")).lower() == "success")
            fail_count = sum(1 for r in fetch_runs if str(r.get("status", "")).lower() != "success")
            a3, a4 = st.columns(2)
            with a3:
                render_metric_card("Recent Success", str(success_count))
            with a4:
                render_metric_card("Recent Failed", str(fail_count))

            run_rows = [
                {
                    "run_id": r.get("id"),
                    "profile_id": r.get("profile_id"),
                    "status": r.get("status"),
                    "started_at": r.get("started_at"),
                    "finished_at": r.get("finished_at"),
                    "inserted": r.get("jobs_inserted"),
                    "duplicates": r.get("duplicates_skipped"),
                    "errors": r.get("errors"),
                }
                for r in fetch_runs[:12]
            ]
            st.dataframe(run_rows, use_container_width=True, hide_index=True)


def _profile_page() -> None:
    render_page_header(
        "Profile Setup",
        "Create job-search context for each user. This guides filtering, scoring, and recommendations.",
        icon=ICON["profile"],
    )

    profiles = get_profiles()
    options = ["Create New"] + profiles
    active = get_active_profile() or "Create New"
    idx = options.index(active) if active in options else 0
    selected = st.selectbox("Choose profile", options=options, index=idx)

    base = load_profile_data(selected if selected != "Create New" else None)
    if selected == "Create New":
        base["user_id"] = ""
        base["display_name"] = ""

    left, right = st.columns([1.45, 1.0])
    with left:
        submitted, profile, _ = render_profile_form(base)
        set_active_toggle = st.checkbox("Set as active profile", value=(selected == active and selected != "Create New"))

        if submitted:
            if not profile.get("user_id"):
                st.error("User ID is required.")
            else:
                path = save_profile_data(profile, set_active=set_active_toggle)
                st.success(f"Profile saved to {path}")
                st.rerun()

    with right:
        selected_kw = render_keyword_assistant()
        if selected_kw:
            st.caption("Selected keywords")
            render_chip_row(selected_kw)
            if action_button(
                "Apply selected keywords to current profile skills",
                action_name="Apply Keywords To Profile",
                use_container_width=True,
            ):
                current_skills = [str(x) for x in base.get("skills", [])]
                merged = sorted(set(current_skills + selected_kw))
                base["skills"] = merged
                path = save_profile_data(base, set_active=False)
                st.success(f"Updated profile skills in {path}")
                st.rerun()

        st.markdown("### Resume Intake")
        st.caption("Upload base resume (PDF/DOCX/TXT/MD). It will be normalized to per-profile base_resume.md.")
        resume_file = st.file_uploader(
            "Upload base resume",
            type=["pdf", "docx", "txt", "md"],
            key="profile_resume_upload",
        )
        current_user_id = str(base.get("user_id", "")).strip() or str(selected if selected != "Create New" else "").strip()
        if action_button("Save Base Resume", action_name="Save Base Resume", use_container_width=True):
            if not current_user_id:
                st.warning("Set a valid user_id first, then save the profile.")
            elif resume_file is None:
                st.warning("Please choose a resume file first.")
            else:
                result = save_base_resume(
                    user_id=current_user_id,
                    filename=str(resume_file.name),
                    content=resume_file.getvalue(),
                )
                st.success(f"Saved resume for {result['user_id']} at {result['canonical_markdown_path']}")
                if not result["parsed_ok"]:
                    st.info("Auto-extraction was limited. Please review and edit base_resume.md manually.")
                else:
                    st.caption(f"Extracted characters: {result['char_count']}")

        st.markdown("### Profile Source Files")
        st.caption("Each profile can maintain separate CSV sources for companies, LinkedIn imports, and manual imports.")
        profile_slug = str(base.get("user_id", "")).strip() or str(selected if selected != "Create New" else "").strip()
        if profile_slug:
            source_dir = profile_source_dir(profile_slug)
            st.code(str(source_dir), language="text")
            if action_button(
                "Initialize/Refresh Profile Source Files",
                action_name="Initialize Profile Source Files",
                use_container_width=True,
            ):
                paths = bootstrap_profile_sources(
                    profile_id=profile_slug,
                    companies_csv="config/target_companies.csv",
                    linkedin_csv="config/linkedin_jobs.csv",
                    manual_jobs_csv="config/manual_jobs.csv",
                )
                st.success("Profile source files are ready.")
                st.json(paths)


def _ingestion_page() -> None:
    render_page_header(
        "Job Ingestion",
        "Step-by-step ingestion flow: add sources, run ingestion, review imports, then score and triage.",
        icon=ICON["ingest"],
    )

    st.markdown("### Ingestion Workflow")
    flow_cols = st.columns(4)
    labels = ["1) Add Source URLs", "2) Run Ingestion", "3) Review Imported Jobs", "4) Score + Pipeline"]
    for col, label in zip(flow_cols, labels):
        with col:
            st.markdown(f"- {label}")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            companies_csv = st.text_input("Companies CSV", value="config/target_companies.csv")
            linkedin_csv = st.text_input("LinkedIn CSV", value="config/linkedin_jobs.csv")
        with c2:
            manual_jobs_csv = st.text_input("Manual jobs CSV", value="config/manual_jobs.csv")
            user_id = st.text_input("Run for user_id (optional)", value=(get_active_profile() or ""))

        if action_button("Run Job Ingestion", action_name="Run Job Ingestion", use_container_width=True):
            prog = st.progress(0)
            status = st.empty()
            for pct, msg in [(10, "Validating inputs"), (35, "Collecting jobs"), (70, "Scoring and saving"), (95, "Generating digest")]:
                prog.progress(pct)
                status.info(msg)
                time.sleep(0.15)

            result = run_job_ingestion(
                db_path=st.session_state["db_path"],
                companies_csv=companies_csv,
                linkedin_csv=linkedin_csv,
                manual_jobs_csv=manual_jobs_csv,
                user_id=user_id.strip() or None,
            )
            st.session_state["last_ingest_summary"] = result
            prog.progress(100)
            status.success("Completed")

    with st.container(border=True):
        st.markdown("### Single URL Ingestion")
        url = st.text_input("Job URL", placeholder="https://boards.greenhouse.io/.../jobs/123")
        single_user = st.text_input("Profile for this URL", value=(get_active_profile() or ""), key="single_url_user")
        if action_button("Ingest This URL", action_name="Ingest Single URL"):
            if not url.strip():
                st.warning("Please provide a URL.")
            else:
                with st.spinner("Extracting and scoring job..."):
                    result = ingest_single_job_url(url.strip(), st.session_state["db_path"], single_user.strip() or None)
                st.json(result)

    if st.session_state.get("last_ingest_summary"):
        st.markdown("### Last Run Status")
        st.json(st.session_state["last_ingest_summary"])

    st.markdown("### Recently Ingested Jobs")
    rows = get_jobs(st.session_state["db_path"], user_id=user_id.strip() or None, limit=150)
    today = date.today().isoformat()
    today_rows = [r for r in rows if str(r.get("date_found", "")) == today]
    render_jobs_table(today_rows)

    st.markdown("### Manage Imported Jobs")
    if not today_rows:
        st.caption("No jobs found for today. Run ingestion first.")
        return

    manager_rows = []
    for r in today_rows:
        manager_rows.append(
            {
                "delete": False,
                "id": int(r.get("id")),
                "title": str(r.get("title", "")),
                "company": str(r.get("company", "")),
                "location": str(r.get("location", "")),
                "job_board": str(r.get("job_board", "")),
                "fit_score": float(r.get("fit_score", 0) or 0),
            }
        )

    edited = st.data_editor(
        pd.DataFrame(manager_rows),
        key="ingest_delete_editor",
        hide_index=True,
        use_container_width=True,
        column_config={
            "delete": st.column_config.CheckboxColumn("Delete", help="Select jobs to delete"),
            "id": st.column_config.NumberColumn("ID", disabled=True, format="%d"),
            "title": st.column_config.TextColumn("Title", disabled=True),
            "company": st.column_config.TextColumn("Company", disabled=True),
            "location": st.column_config.TextColumn("Location", disabled=True),
            "job_board": st.column_config.TextColumn("Source", disabled=True),
            "fit_score": st.column_config.NumberColumn("Fit", disabled=True, format="%.1f"),
        },
        num_rows="fixed",
    )

    selected_ids = [int(row["id"]) for _, row in edited.iterrows() if bool(row.get("delete", False))]
    select_col, delete_col = st.columns([3, 1.2])
    with select_col:
        st.caption(f"Selected for deletion: {len(selected_ids)}")
        confirm_bulk_delete = st.checkbox(
            "I understand selected jobs will be permanently deleted",
            key="confirm_bulk_delete_jobs",
        )
    with delete_col:
        if action_button(
            "Delete Selected Jobs",
            action_name="Delete Selected Ingested Jobs",
            use_container_width=True,
        ):
            if not selected_ids:
                st.warning("Select at least one job to delete.")
            elif not confirm_bulk_delete:
                st.warning("Please confirm deletion before deleting selected jobs.")
            else:
                deleted_count = delete_jobs_by_ids(
                    db_path=st.session_state["db_path"],
                    job_ids=selected_ids,
                    user_id=user_id.strip() or None,
                )
                st.success(f"Deleted {deleted_count} job(s).")
                st.rerun()

    with st.expander("Quick Delete One Job"):
        quick_map = {
            f"#{int(r.get('id'))} | {str(r.get('title','Role'))} @ {str(r.get('company','Company'))}": int(r.get("id"))
            for r in today_rows
        }
        quick_options = list(quick_map.keys())
        quick_choice = st.selectbox("Choose job", options=quick_options, key="quick_delete_job_choice")
        confirm_single_delete = st.checkbox(
            "I understand this job will be permanently deleted",
            key="confirm_single_delete_job",
        )
        if action_button("Delete This Job", action_name="Delete One Ingested Job"):
            delete_id = quick_map.get(quick_choice)
            if delete_id is None:
                st.warning("Please choose a valid job.")
            elif not confirm_single_delete:
                st.warning("Please confirm deletion before deleting this job.")
            else:
                deleted_count = delete_jobs_by_ids(
                    db_path=st.session_state["db_path"],
                    job_ids=[delete_id],
                    user_id=user_id.strip() or None,
                )
                st.success(f"Deleted {deleted_count} job.")
                st.rerun()


def _scoring_page() -> None:
    render_page_header(
        "Job Scoring",
        "Review score quality and keyword coverage before deciding where to apply.",
        icon=ICON["score"],
    )

    user_filter, _ = _resolve_user_filter()
    rows = get_jobs(st.session_state["db_path"], user_id=user_filter, limit=250)
    profile = load_profile_data(user_filter)

    with st.container(border=True):
        s1, s2 = st.columns([4.2, 1.0])
        with s1:
            min_score = st.slider("Minimum fit score", 0.0, 5.0, 0.0, 0.1)
        with s2:
            render_metric_card("Threshold", f"{min_score:.1f}/5", icon=ICON["threshold"])

    filtered = [r for r in rows if float(r.get("fit_score", 0) or 0) >= min_score]
    if not filtered:
        render_empty_state("No scored jobs match", "Try reducing filters or ingest more jobs.", kind="search")
        return

    for job in filtered[:50]:
        with st.container(border=True):
            head1, head2 = st.columns([4, 1.2])
            with head1:
                st.markdown(f"**{job.get('title', 'Unknown')}**")
                st.caption(f"{job.get('company', 'Unknown')} | {job.get('location', 'Unknown')}")
            with head2:
                label, band = score_band(float(job.get("fit_score", 0) or 0))
                render_status_badge(label, band)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption("Visa/Sponsorship")
                st.write(sponsorship_signal(str(job.get("description", ""))))
            with c2:
                st.caption("Matched keywords")
                matched = parse_keywords(job.get("resume_keywords"))
                render_chip_row(matched[:8])
            with c3:
                st.caption("Missing must-have")
                missing = missing_keywords(job, profile)
                render_chip_row(missing[:8])

            st.caption(str(job.get("score_reason", "")))


def _url_validation_page() -> None:
    render_page_header(
        "URL Validation",
        "Validate target company URLs, inspect failures, and apply cleaned targets to scraping.",
        icon="\U0001F9EA",
    )

    default_input = "config/target_companies.csv"
    default_output = "outputs/url_validation"
    input_csv = st.text_input("Input targets CSV", value=default_input)
    output_dir = st.text_input("Output directory", value=default_output)
    c1, c2, c3 = st.columns(3)
    with c1:
        timeout = st.number_input("Timeout (sec)", min_value=2, max_value=30, value=8, step=1)
    with c2:
        max_workers = st.number_input("Max workers", min_value=1, max_value=128, value=24, step=1)
    with c3:
        limit = st.number_input("Limit rows (0=all)", min_value=0, max_value=25000, value=0, step=50)

    if action_button("Run URL Validation", action_name="Run URL Validation", use_container_width=True):
        with st.spinner("Validating URLs..."):
            try:
                summary = run_validation(
                    input_csv=input_csv,
                    output_dir=output_dir,
                    timeout=int(timeout),
                    max_workers=int(max_workers),
                    limit=int(limit),
                    try_suggestions=True,
                )
                st.success("URL validation completed.")
                st.json(summary)
            except Exception as exc:
                st.error(f"Validation failed: {exc}")

    summary_path = Path(output_dir) / "summary.json"
    report_path = Path(output_dir) / "validation_report.csv"
    valid_path = Path(output_dir) / "valid_targets.csv"
    failed_path = Path(output_dir) / "failed_targets.csv"

    st.markdown("### Latest Validation Summary")
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_metric_card("Rows Checked", str(summary.get("rows_checked", 0)))
            with k2:
                ok_total = int(summary.get("valid", 0)) + int(summary.get("redirected", 0)) + int(summary.get("suggested_fix", 0))
                render_metric_card("Usable Targets", str(ok_total))
            with k3:
                render_metric_card("Failed", str(summary.get("failed", 0)))
            with k4:
                render_metric_card("Suggested Fixes", str(summary.get("suggested_fix", 0)))
            st.caption(f"Report: {report_path}")
        except Exception as exc:
            st.error(f"Could not parse summary: {exc}")
    else:
        st.caption("No summary found yet. Run validation first.")

    st.markdown("### Apply Clean Targets")
    st.caption("This will overwrite config/target_companies.csv with valid_targets.csv and create a backup copy.")
    confirm_apply = st.checkbox("I understand this will replace the current target_companies.csv", key="confirm_apply_valid_targets")
    if action_button("Apply valid_targets.csv to target_companies.csv", action_name="Apply Valid Targets", use_container_width=True):
        if not confirm_apply:
            st.warning("Please confirm replacement first.")
        elif not valid_path.exists():
            st.warning("valid_targets.csv not found. Run validation first.")
        else:
            target_path = Path("config/target_companies.csv")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                backup_name = f"target_companies.backup.{date.today().isoformat()}.csv"
                backup_path = target_path.parent / backup_name
                shutil.copy2(target_path, backup_path)
                st.caption(f"Backup created: {backup_path}")
            shutil.copy2(valid_path, target_path)
            st.success("Applied valid targets successfully.")

    st.markdown("### Apply Suggested Fixes Only")
    st.caption("This updates only rows with URL fixes from validation_report.csv and leaves all other rows unchanged.")
    confirm_apply_suggested = st.checkbox(
        "I understand this will update matching rows in target_companies.csv",
        key="confirm_apply_suggested_fixes",
    )
    if action_button("Apply suggested fixes only", action_name="Apply Suggested URL Fixes", use_container_width=True):
        target_path = Path("config/target_companies.csv")
        if not confirm_apply_suggested:
            st.warning("Please confirm before applying suggested fixes.")
        elif not report_path.exists():
            st.warning("validation_report.csv not found. Run validation first.")
        elif not target_path.exists():
            st.warning("config/target_companies.csv was not found.")
        else:
            try:
                report_df = pd.read_csv(report_path)
                target_df = pd.read_csv(target_path)
                # Suggested rows include both explicit suggestions and successful redirects.
                fix_df = report_df[
                    report_df["outcome"].isin(["suggested_fix", "redirected"])
                ][["company_name", "best_url"]].dropna()
                fix_map = {
                    str(row["company_name"]).strip().lower(): str(row["best_url"]).strip()
                    for _, row in fix_df.iterrows()
                    if str(row.get("company_name", "")).strip() and str(row.get("best_url", "")).strip()
                }

                if not fix_map:
                    st.info("No suggested fixes available to apply.")
                else:
                    backup_name = f"target_companies.backup.suggested.{date.today().isoformat()}.csv"
                    backup_path = target_path.parent / backup_name
                    shutil.copy2(target_path, backup_path)

                    updated = 0
                    for idx, row in target_df.iterrows():
                        key = str(row.get("company_name", "")).strip().lower()
                        if key in fix_map:
                            new_url = fix_map[key]
                            old_url = str(row.get("careers_url", "")).strip()
                            if new_url and new_url != old_url:
                                target_df.at[idx, "careers_url"] = new_url
                                updated += 1

                    target_df.to_csv(target_path, index=False)
                    st.success(f"Applied suggested fixes to {updated} row(s). Backup: {backup_path}")
            except Exception as exc:
                st.error(f"Could not apply suggested fixes: {exc}")

    st.markdown("### Validation Tables")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("**Valid Targets (sample)**")
        if valid_path.exists():
            st.dataframe(pd.read_csv(valid_path).head(25), use_container_width=True, hide_index=True)
        else:
            st.caption("No valid_targets.csv found.")
    with t2:
        st.markdown("**Failed Targets (sample)**")
        if failed_path.exists():
            st.dataframe(pd.read_csv(failed_path).head(25), use_container_width=True, hide_index=True)
        else:
            st.caption("No failed_targets.csv found.")


def _how_to_use_page() -> None:
    render_page_header(
        "How To Use PM Copilot",
        "A practical step-by-step guide to onboard, ingest, score, and run your application pipeline effectively.",
        icon=ICON["howto"],
    )

    st.markdown("### 1) Set Up Profile")
    st.markdown(
        f"- Go to **{ICON['profile']} Profile Setup**.\n"
        "- Fill your role goals, locations, seniority, skills, and compensation needs.\n"
        "- Paste sample JDs in Keyword Assistant to capture recurring terms.\n"
        "- Save and set profile active."
    )

    st.markdown("### 2) Ingest Jobs")
    st.markdown(
        f"- Go to **{ICON['ingest']} Ingest Jobs**.\n"
        "- Confirm CSV sources (`target_companies.csv`, `linkedin_jobs.csv`, `manual_jobs.csv`).\n"
        "- Click **Run Job Ingestion**.\n"
        "- Review import summary and recently ingested rows."
    )

    st.markdown("### 3) Evaluate Fit")
    st.markdown(
        f"- Go to **{ICON['score']} Score Jobs**.\n"
        "- Use **Minimum fit score** slider to prioritize best roles.\n"
        "- Review matched keywords, missing keywords, and sponsorship signal.\n"
        "- Focus on strong-fit and possible-fit roles first."
    )

    st.markdown("### 4) Manage Pipeline")
    st.markdown(
        f"- Go to **{ICON['pipeline']} Pipeline**.\n"
        "- Move jobs through statuses (Saved -> Applied -> Recruiter Screen -> Interview -> Offer).\n"
        "- Add notes and next actions per card."
    )

    st.markdown("### 5) Review Analytics Weekly")
    st.markdown(
        f"- Go to **{ICON['analytics']} Analytics**.\n"
        "- Track response rate, source performance, status funnel, and company spread.\n"
        "- Adjust profile and source mix based on outcomes."
    )

    st.markdown("### Daily Routine (Recommended)")
    st.info("Morning: run ingestion | Afternoon: score + shortlist | Evening: move pipeline + set follow-ups.")


def _run_history_page() -> None:
    render_page_header(
        "Run History",
        "Inspect hourly automation runs, filter outcomes, export logs, and retry failed profiles.",
        icon="\U0001F4DD",
    )

    runs = get_fetch_runs(st.session_state["db_path"], profile_id=None, limit=1000)
    if not runs:
        render_empty_state("No run history yet", "Run hourly ingestion to populate automation history.", kind="search")
        return

    df = pd.DataFrame(runs)
    for col in ["profile_id", "status", "run_type", "started_at", "finished_at"]:
        if col not in df.columns:
            df[col] = ""

    left, right = st.columns([2.3, 1.2])
    with left:
        profile_options = sorted([x for x in df["profile_id"].fillna("").unique().tolist() if str(x).strip()])
        selected_profiles = st.multiselect("Profiles", options=profile_options, default=profile_options[:8])
    with right:
        status_options = sorted([x for x in df["status"].fillna("").unique().tolist() if str(x).strip()])
        selected_status = st.multiselect("Statuses", options=status_options, default=status_options)

    type_options = sorted([x for x in df["run_type"].fillna("").unique().tolist() if str(x).strip()])
    selected_types = st.multiselect("Run types", options=type_options, default=type_options)

    filtered = df.copy()
    if selected_profiles:
        filtered = filtered[filtered["profile_id"].isin(selected_profiles)]
    if selected_status:
        filtered = filtered[filtered["status"].isin(selected_status)]
    if selected_types:
        filtered = filtered[filtered["run_type"].isin(selected_types)]

    total_runs = len(filtered)
    success_runs = int((filtered["status"].astype(str).str.lower() == "success").sum()) if total_runs else 0
    failed_runs = total_runs - success_runs
    inserted_total = int(filtered.get("jobs_inserted", pd.Series(dtype=int)).fillna(0).sum()) if total_runs else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_metric_card("Runs", str(total_runs))
    with k2:
        render_metric_card("Success", str(success_runs))
    with k3:
        render_metric_card("Failed", str(failed_runs))
    with k4:
        render_metric_card("Jobs Inserted", str(inserted_total))

    view_cols = [
        "id",
        "run_type",
        "profile_id",
        "status",
        "started_at",
        "finished_at",
        "companies_processed",
        "jobs_scraped",
        "jobs_inserted",
        "duplicates_skipped",
        "errors",
        "notes",
    ]
    present_cols = [c for c in view_cols if c in filtered.columns]
    st.dataframe(filtered[present_cols], use_container_width=True, hide_index=True)

    csv_data = filtered[present_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered runs as CSV",
        data=csv_data,
        file_name=f"fetch_runs_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("### Retry Failed Profiles")
    failed_df = filtered[filtered["status"].astype(str).str.lower() != "success"]
    failed_profiles = sorted({str(x).strip() for x in failed_df["profile_id"].fillna("").tolist() if str(x).strip()})
    if not failed_profiles:
        st.caption("No failed profiles in current filtered view.")
        return

    latest_failed_df = (
        failed_df.sort_values(by="id", ascending=False)
        .drop_duplicates(subset=["profile_id"], keep="first")
        .copy()
    )
    latest_failed_profiles = sorted(
        {str(x).strip() for x in latest_failed_df["profile_id"].fillna("").tolist() if str(x).strip()}
    )

    st.caption(f"Detected failed profiles: {', '.join(failed_profiles)}")
    st.caption(f"Latest failed per profile: {', '.join(latest_failed_profiles)}")
    confirm_retry = st.checkbox(
        "I understand this will re-run scraping for the failed profiles",
        key="confirm_retry_failed_profiles",
    )
    retry_timeout = st.number_input("Retry timeout (seconds)", min_value=5, max_value=60, value=20, step=1)
    b1, b2 = st.columns(2)
    with b1:
        retry_all = action_button(
            "Retry All Failed Profiles",
            action_name="Retry All Failed Profiles",
            use_container_width=True,
        )
        st.caption("Use this when you want to retry every failed profile in the current filtered view.")
    with b2:
        retry_latest = action_button(
            "Retry Latest Failed Per Profile",
            action_name="Retry Latest Failed Per Profile",
            use_container_width=True,
        )
        st.caption("Use this when there are multiple failures per profile and you only want one retry per profile.")

    if retry_all or retry_latest:
        if not confirm_retry:
            st.warning("Please confirm before retrying failed profiles.")
        else:
            retry_profiles = latest_failed_profiles if retry_latest else failed_profiles
            if not retry_profiles:
                st.warning("No failed profiles available for the selected retry mode.")
                return
            with st.spinner("Retrying failed profiles..."):
                try:
                    summary_name = "hourly_retry_latest_summary.json" if retry_latest else "hourly_retry_summary.json"
                    summary_path = f"outputs/{summary_name}"
                    summary = run_hourly(
                        companies_csv="config/target_companies.csv",
                        linkedin_csv="config/linkedin_jobs.csv",
                        manual_jobs_csv="config/manual_jobs.csv",
                        db_path=st.session_state["db_path"],
                        profiles=retry_profiles,
                        timeout=int(retry_timeout),
                        summary_path=summary_path,
                    )
                    st.success(f"Retry run completed. Saved to {summary_path}")
                    st.json(summary)
                except Exception as exc:
                    st.error(f"Retry failed: {exc}")


def _pipeline_page() -> None:
    render_page_header(
        "Application Pipeline",
        "Manage statuses with a clean Kanban workflow. Use this as your Notion-style operating board.",
        icon=ICON["pipeline"],
    )

    user_filter, _ = _resolve_user_filter()
    rows = get_jobs(st.session_state["db_path"], user_id=user_filter, limit=800)

    cols = st.columns(len(PIPELINE_COLUMNS))
    for idx, (column, statuses) in enumerate(PIPELINE_COLUMNS.items()):
        with cols[idx]:
            scoped = [r for r in rows if str(r.get("status", "New")) in statuses]
            st.markdown(f"**{column} ({len(scoped)})**")
            for job in scoped[:20]:
                with st.container(border=True):
                    st.markdown(f"`#{job.get('id')}` {job.get('title', 'Role')}")
                    st.caption(f"{job.get('company', 'Company')} | {float(job.get('fit_score', 0) or 0):.1f}/5")
                    next_status = st.selectbox(
                        "Move",
                        options=PIPELINE_STATUSES,
                        index=PIPELINE_STATUSES.index(str(job.get("status", "Saved")))
                        if str(job.get("status", "Saved")) in PIPELINE_STATUSES
                        else 0,
                        key=f"pipe_move_{job.get('id')}",
                        label_visibility="collapsed",
                    )
                    notes = st.text_input("Next action / note", value=str(job.get("notes") or ""), key=f"pipe_note_{job.get('id')}")
                    if action_button(
                        "Save",
                        key=f"pipe_save_{job.get('id')}",
                        action_name=f"Save Pipeline Card #{job.get('id')}",
                        use_container_width=True,
                    ):
                        save_job_update(
                            db_path=st.session_state["db_path"],
                            job_id=int(job.get("id")),
                            status=next_status,
                            notes=notes,
                            applied_date=date.today().isoformat() if next_status == "Applied" else None,
                        )
                        st.rerun()


def _analytics_page() -> None:
    render_page_header(
        "Analytics",
        "Track pipeline performance, source quality, and response outcomes with clean visuals.",
        icon=ICON["analytics"],
    )

    user_filter, _ = _resolve_user_filter()
    rows = get_jobs(st.session_state["db_path"], user_id=user_filter, limit=3000)
    render_analytics_charts(rows)

    st.markdown("### Additional Insights")
    statuses = Counter(str(r.get("status", "New")) for r in rows)
    applied = statuses.get("Applied", 0) + statuses.get("Interview", 0) + statuses.get("Offer", 0)
    responses = statuses.get("Interview", 0) + statuses.get("Offer", 0)
    response_rate = (responses / applied * 100.0) if applied else 0.0

    a1, a2 = st.columns(2)
    with a1:
        render_metric_card("Response Rate", f"{response_rate:.1f}%", icon=ICON["response_rate"])
    with a2:
        applied_companies = len(
            set(str(r.get("company", "")) for r in rows if str(r.get("status", "")) in {"Applied", "Interview", "Offer"})
        )
        render_metric_card("Companies Applied To", str(applied_companies), icon=ICON["companies"])

    keywords = Counter()
    for row in rows:
        for kw in parse_keywords(row.get("resume_keywords")):
            keywords[str(kw).strip().lower()] += 1
    st.markdown("### Top Matched Keywords")
    render_chip_row([f"{k} ({v})" for k, v in keywords.most_common(15)])


def _settings_page() -> None:
    render_page_header(
        "Settings",
        "Configure workspace paths and profile defaults. Keep these stable for automation runs.",
        icon=ICON["settings"],
    )

    current = st.session_state["db_path"]
    db_path = st.text_input("Database path", value=current)
    if action_button("Apply DB Path", action_name="Apply DB Path"):
        st.session_state["db_path"] = db_path
        ensure_db(db_path)
        st.success("Database path applied.")

    profiles = get_profiles()
    active = get_active_profile()
    if profiles:
        idx = profiles.index(active) if active in profiles else 0
        chosen = st.selectbox("Active profile", options=profiles, index=idx)
        if action_button("Set Active Profile", action_name="Set Active Profile"):
            set_active_profile(chosen)
            st.success(f"Active profile set to {chosen}")

    st.caption("Recommended: keep DB in `data/jobs.db` for local-first reliability.")


def main() -> None:
    st.set_page_config(page_title="PM Copilot", page_icon="\U0001F4BC", layout="wide")
    _init_state()
    apply_theme()

    ensure_db(st.session_state["db_path"])
    active = get_active_profile()
    page = render_sidebar(st.session_state["db_path"], active_profile=active, db_exists=True)

    if page == "dashboard":
        _dashboard_page()
    elif page == "profile":
        _profile_page()
    elif page == "ingest":
        _ingestion_page()
    elif page == "url_validation":
        _url_validation_page()
    elif page == "run_history":
        _run_history_page()
    elif page == "score":
        _scoring_page()
    elif page == "pipeline":
        _pipeline_page()
    elif page == "analytics":
        _analytics_page()
    elif page == "howto":
        _how_to_use_page()
    else:
        _settings_page()


if __name__ == "__main__":
    main()
