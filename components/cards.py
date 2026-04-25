from __future__ import annotations

from textwrap import dedent
from typing import Iterable

import streamlit as st

from components.actions import action_button


def render_page_header(
    title: str,
    subtitle: str,
    cta_label: str | None = None,
    cta_key: str | None = None,
    icon: str = "briefcase",
) -> bool:
    clicked = False
    with st.container(border=True):
        if cta_label:
            top_left, top_right = st.columns([5, 1.5], vertical_alignment="center")
            with top_left:
                st.markdown(
                    dedent(
                        f"""
                        <div class="pc-hero-inner">
                          <div class="pc-row pc-header-row">
                            <span class="pc-icon">{icon}</span>
                            <div class="pc-title">{title}</div>
                          </div>
                          <div class="pc-subtitle">{subtitle}</div>
                        </div>
                        """
                    ).strip(),
                    unsafe_allow_html=True,
                )
            with top_right:
                clicked = action_button(
                    cta_label,
                    key=cta_key or f"cta_{title}",
                    action_name=cta_label,
                    use_container_width=True,
                )
        else:
            st.markdown(
                dedent(
                    f"""
                    <div class="pc-hero-inner">
                      <div class="pc-row pc-header-row">
                        <span class="pc-icon">{icon}</span>
                        <div class="pc-title">{title}</div>
                      </div>
                      <div class="pc-subtitle">{subtitle}</div>
                    </div>
                    """
                ).strip(),
                unsafe_allow_html=True,
            )
    return clicked


def render_section_card(title: str, helper: str | None = None) -> None:
    helper_html = f'<div class="pc-helper">{helper}</div>' if helper else ""
    st.markdown(
        dedent(
            f"""
            <div class="pc-card">
              <div class="pc-section-title">{title}</div>
              {helper_html}
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, icon: str = "•") -> None:
    st.markdown(
        dedent(
            f"""
            <div class="pc-kpi-card">
              <div class="pc-kpi-head">
                <div class="pc-kpi-label">{label}</div>
              </div>
              <div class="pc-kpi-value">{value}</div>
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_keyword_chip(text: str) -> None:
    st.markdown(f'<span class="pc-chip">{text}</span>', unsafe_allow_html=True)


def render_chip_row(items: Iterable[str]) -> None:
    html = "".join([f'<span class="pc-chip">{item}</span>' for item in items if str(item).strip()])
    if not html:
        st.caption("No items")
        return
    st.markdown(html, unsafe_allow_html=True)


def render_status_badge(label: str, band: str) -> None:
    klass = "pc-badge-mid"
    if band == "strong":
        klass = "pc-badge-ok"
    elif band == "low":
        klass = "pc-badge-low"
    st.markdown(f'<span class="pc-badge {klass}">{label}</span>', unsafe_allow_html=True)


def render_job_card(title: str, company: str, location: str, fit_score: float, summary: str) -> None:
    st.markdown(
        dedent(
            f"""
            <div class="pc-card" style="margin-bottom:0.6rem;">
              <div style="font-weight:700; color:#111827; margin-bottom:0.2rem;">{title}</div>
              <div style="font-size:0.88rem; color:#4B5563; margin-bottom:0.35rem;">{company} | {location}</div>
              <div style="font-size:0.84rem; color:#0A66C2; font-weight:600; margin-bottom:0.35rem;">Fit Score: {fit_score:.1f}/5</div>
              <div style="font-size:0.82rem; color:#6B7280; line-height:1.4;">{summary}</div>
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )
