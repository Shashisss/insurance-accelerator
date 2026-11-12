"""Insurance Semantic Layer — one app, three decisions.

The sidebar selects the use case; each screen renders inside this single page.
That keeps the deployment simple (no multipage discovery, no per-page config)
and makes the three use cases comparable side by side.

    streamlit run streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

from iaa.screen_claims import render as render_claims
from iaa.screen_fleet import render as render_fleet
from iaa.screen_pricing import render as render_pricing

st.set_page_config(page_title="Insurance Semantic Layer", page_icon="🏢", layout="wide",
                   initial_sidebar_state="expanded")

SCREENS = {
    "Fleet renewal": render_fleet,
    "Claims reserving": render_claims,
    "Pricing adequacy": render_pricing,
}

with st.sidebar:
    st.markdown("### Use case")
    choice = st.radio(
        "Use case",
        list(SCREENS),
        index=0,
        label_visibility="collapsed",
        key="usecase",
    )
    st.caption("One model, one evidence contract, three decisions.")

SCREENS[choice]()
