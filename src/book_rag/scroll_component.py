"""A helper without a visible part: scrolls the chat to its newest message when a new answer has been drawn."""

import streamlit as st

_JS = """
export default function ({ data, parentElement }) {
  const doc = parentElement.ownerDocument
  const win = doc.defaultView
  if (win.__bookRagScrolled === data.count) return // the same chat: leave the reader where they scrolled to
  win.__bookRagScrolled = data.count
  const down = () => {
    const pane = doc.querySelector(data.selector)
    if (pane) pane.scrollTop = pane.scrollHeight
  }
  win.requestAnimationFrame(down)
  win.setTimeout(down, 150) // again once the passages and the layout have settled
  win.setTimeout(down, 500)
}
"""

_SCROLLER = st.components.v2.component("chat_scroller", js=_JS)


def scroll_to_newest(count: int, selector: str = ".st-key-chat-pane") -> None:
    """Scroll the element `selector` to its end whenever `count` (the number of messages) changes."""
    _SCROLLER(data={"count": count, "selector": selector}, key="chat-scroller-component")
