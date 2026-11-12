"""Shared 'ask' panel — the same AI surface on every use case.

Each page passes its own suggested questions and a key prefix so the three
panels keep separate state. The panel is deliberately thin: it renders, it
calls `assistant.ask`, and it shows the tool trace. All the guardrails live in
`assistant.py`, so every page inherits them.
"""

from __future__ import annotations

from typing import Any, Sequence

import pandas as pd
import streamlit as st

from .assistant import Toolbox, ask, llm_configured


def render_ask_panel(toolbox: Toolbox, suggestions: Sequence[str], key_prefix: str,
                     title: str = "Ask this book a question") -> None:
    state_key = f"{key_prefix}_answer"
    question_key = f"{key_prefix}_question"

    mode = "model" if llm_configured() else "deterministic (no model configured)"

    with st.container(border=True):
        st.markdown(f"### {title}")
        st.caption(
            "Answered by calling the same functions that drew this page — the assistant routes and "
            f"phrases, it never calculates, and any figure not returned by a tool is rejected. Mode: **{mode}**."
        )

        def _run(question: str) -> None:
            with st.spinner("Routing to tools…"):
                try:
                    answer = ask(question, toolbox)
                    st.session_state[state_key] = answer.as_dict()
                except Exception as exc:  # keep the demo alive
                    st.session_state[state_key] = {
                        "text": f"Error: {exc}", "tool": "-", "args": {},
                        "mode": mode, "guardrail": None, "trace": [], "detail": None,
                    }
                st.session_state[question_key] = question

        st.markdown("**Try one:**")
        cols = st.columns(len(suggestions))
        for col, question in zip(cols, suggestions):
            if col.button(question, key=f"{key_prefix}::sugg::{question}"):
                _run(question)

        with st.form(f"{key_prefix}_ask_form", clear_on_submit=False, border=False):
            typed = st.text_input(
                "Or ask your own",
                placeholder="ask in plain English…",
                label_visibility="collapsed",
                key=f"{key_prefix}_input",
            )
            if st.form_submit_button("Ask", type="primary") and typed.strip():
                _run(typed.strip())

        stored: dict[str, Any] | None = st.session_state.get(state_key)
        if stored:
            asked = st.session_state.get(question_key, "")
            if asked:
                st.markdown(f"**Q:** {asked}")
            st.success(stored["text"])
            if stored.get("guardrail"):
                st.warning(f"Guardrail: {stored['guardrail']}")
            with st.expander("How this was produced — tool, arguments, verification"):
                st.markdown(f"**Tool called:** `{stored['tool']}`  \n**Arguments:** `{stored['args']}`")
                st.dataframe(pd.DataFrame(stored["trace"]), hide_index=True, width="stretch")
                if stored.get("detail"):
                    st.json(stored["detail"])
