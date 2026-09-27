"""Vetted advisor route."""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Vetted | Advisor Desk",
    page_icon=Path(__file__).resolve().parents[1] / "assets" / "vetted-mark.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from ui import render_advisor

render_advisor()
