"""The changes page: how this app differs from the notebook and the original assignment."""

import streamlit as st

from book_rag.config import PROJECT_ROOT

st.markdown((PROJECT_ROOT / "docs" / "changes.md").read_text(encoding="utf-8"))
