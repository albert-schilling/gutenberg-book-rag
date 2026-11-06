"""The settings page: choices that change how the companion answers."""

import streamlit as st

from book_rag.config import AGENTIC_DEFAULT, LLM_MODEL, LLM_PROVIDER, REFUSAL_RULE, SOFT_REFUSAL_RULE


def remember_agent_choice():
    # The widget is only drawn on this page and Streamlit forgets the state of a widget that is not drawn:
    # the choice is copied to a key of its own, which the chat page reads.
    st.session_state["agentic_on"] = st.session_state["agentic_widget"]


st.subheader("Answers")
st.toggle(
    "Search again when needed",
    value=st.session_state.get("agentic_on", AGENTIC_DEFAULT),
    key="agentic_widget",
    on_change=remember_agent_choice,
    help="The model may rephrase your question and search the book again before it answers.",
)
st.caption(
    "Off by default. When it is on, the model can write new search questions if the first passages do not answer yours, and the "
    "searches are shown under the answer. On 51 questions that the system was not tuned on it did not answer facts better, and it "
    "uses 1.7 to 3.2 calls per question instead of one. It may help questions about the whole book (only 3 were tested). "
    "The free plans limit the tokens per minute and per day, so more calls mean more waiting. "
    "The setting lasts for this browser session."
)

st.subheader("Language model")
st.caption(
    f"{LLM_PROVIDER.capitalize()}, model `{LLM_MODEL}`. Change it with `BOOK_RAG_LLM` (mistral or groq) in the `.env` file, "
    "then restart the app."
)
st.caption(
    "Refusal rule: "
    + (
        "soft, the model answers when the passages contain the information even in part."
        if REFUSAL_RULE == SOFT_REFUSAL_RULE
        else "strict, the model refuses unless the passages answer the question."
    )
    + " Change it with `BOOK_RAG_REFUSAL` (soft or strict)."
)
