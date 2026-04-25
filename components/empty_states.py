from __future__ import annotations

import re

import streamlit as st


ILLUSTRATIONS = {
    "blank": """
    <svg width="116" height="70" viewBox="0 0 116 70" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="14" width="100" height="46" rx="9" fill="#F8FAFC" stroke="#D7DEE8"/>
      <rect x="18" y="24" width="42" height="6" rx="3" fill="#CFE1F8"/>
      <rect x="18" y="35" width="78" height="5" rx="2.5" fill="#E5E7EB"/>
      <rect x="18" y="44" width="58" height="5" rx="2.5" fill="#E5E7EB"/>
      <circle cx="88" cy="27" r="8" fill="#EAF3FF" stroke="#B9D2F0"/>
      <path d="M84 27h8M88 23v8" stroke="#0A66C2" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    """,
    "search": """
    <svg width="116" height="70" viewBox="0 0 116 70" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="18" width="62" height="36" rx="8" fill="#F8FAFC" stroke="#D7DEE8"/>
      <circle cx="52" cy="35" r="14" fill="#EAF3FF" stroke="#B9D2F0"/>
      <circle cx="52" cy="35" r="6" stroke="#0A66C2" stroke-width="1.6"/>
      <path d="M56.8 39.8L63 46" stroke="#0A66C2" stroke-width="1.6" stroke-linecap="round"/>
      <rect x="77" y="26" width="28" height="22" rx="6" fill="#FFF1F2" stroke="#FFD1D4"/>
      <rect x="83" y="32" width="16" height="4" rx="2" fill="#FF9BA0"/>
    </svg>
    """,
}


def _clean_text(value: str) -> str:
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


def render_empty_state(title: str, subtitle: str, kind: str = "blank") -> None:
    # Defensive cleanup prevents accidental raw HTML from surfacing in empty states.
    clean_title = _clean_text(title)
    clean_subtitle = _clean_text(subtitle)
    art = ILLUSTRATIONS.get(kind, ILLUSTRATIONS["blank"])
    art_compact = " ".join(art.split())
    html = (
        f'<div class="pc-empty">'
        f"{art_compact}"
        f'<div class="pc-empty-title">{clean_title}</div>'
        f'<div class="pc-empty-sub">{clean_subtitle}</div>'
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)
