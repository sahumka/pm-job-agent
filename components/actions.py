from __future__ import annotations

from datetime import datetime

import streamlit as st


def _record_action(action_name: str) -> None:
    stamp = datetime.now().strftime("%I:%M:%S %p").lstrip("0")
    st.session_state["last_action_name"] = action_name
    st.session_state["last_action_time"] = stamp


def action_button(
    label: str,
    *,
    key: str | None = None,
    action_name: str | None = None,
    use_container_width: bool = False,
) -> bool:
    clicked = st.button(label, key=key, use_container_width=use_container_width)
    if clicked:
        _record_action(action_name or label)
    return clicked


def action_submit_button(
    label: str,
    *,
    action_name: str | None = None,
    use_container_width: bool = False,
) -> bool:
    clicked = st.form_submit_button(label, use_container_width=use_container_width)
    if clicked:
        _record_action(action_name or label)
    return clicked

