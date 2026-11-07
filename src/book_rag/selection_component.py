"""The "Ask about this" tooltip for selected text, as a Streamlit component."""

from pathlib import Path

import streamlit as st

# Declared once, when the module is imported
_SELECTION = st.components.v2.component(
    "text_selection",
    html="<span></span>",
    js=(Path(__file__).parent / "selection.js").read_text(encoding="utf-8"),
)


def text_selection() -> str | None:
    """Mount the tooltip. Returns the selected text in the run that follows a click on "Ask about this"."""
    result = _SELECTION(key="text-selection", on_ask_change=lambda: None, height="content")
    return result.ask or None
