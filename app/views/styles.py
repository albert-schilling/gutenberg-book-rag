"""Page styles: a CSS file next to the pages, injected into the page that asks for it."""

from pathlib import Path

import streamlit as st

_HERE = Path(__file__).parent


def inject(name: str) -> None:
    """Add `<name>.css` to the page. Only the page that calls it gets the styles."""
    st.html(f"<style>{(_HERE / f'{name}.css').read_text(encoding='utf-8')}</style>")
