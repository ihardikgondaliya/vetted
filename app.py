"""Vetted application entry point and URL route registry."""

from pathlib import Path

import streamlit as st

from database import init_db


st.set_page_config(
    page_title="Vetted | Deal Readiness",
    page_icon=Path(__file__).resolve().parent / "assets" / "vetted-mark.png",
    layout="wide",
)
init_db()

st.navigation(
    [
        st.Page("pages/home.py", title="Vetted", url_path="", default=True),
        st.Page("pages/advisor.py", title="Advisor", url_path="advisor"),
        st.Page("pages/business.py", title="Business", url_path="business"),
    ],
    position="hidden",
).run()
