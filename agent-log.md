# Agent log

What the agent did while you were away, one short entry per task. Frictions and things that could not be done as
asked are listed under each task and in the last section.

## Ground rules I followed
- Work on branch `agent/assignments`, one commit per task, only my own files (your `.claude/` and `.agents/` are untouched).
- "Grok" is read as **Groq**. Real limits of the free account, measured from the response headers: **1,000 requests/day
  and 8,000 tokens/minute** per model. Prompts are kept small, extra LLM calls are bounded, and the browser tests run in
  an offline mode that never calls Groq.
- Task 7 is cut off after "He should then return"; I read it as: return the final answer together with the questions
  that were used.
- You asked for commits in this batch. Your stored preference says "the user handles git", so I committed only because
  you asked explicitly, and only on the branch.

## 1. changes.md update and browser tests (done)
- `docs/changes.md`: added rows for the web app, the tests and the offline mode.
- `tests/browser/`: 6 Playwright tests (headless Chromium) against the real app, started by a fixture with its own
  vector store: the book opens at its start with a small window; scrolling down loads lazily up to the end and never
  keeps more than 250 paragraphs; no text jump while paragraphs are added/dropped (long book); scrolling up from a
  passage; the passage opens highlighted and in view; Close. Run: `uv run playwright install chromium`, then
  `uv run pytest -m browser` (about 40 s, skipped if no browser).
- Added **offline mode** (`BOOK_RAG_OFFLINE=1`): the LLM is replaced by a fixed reply, so the browser tests use no Groq quota.
- Mutation check: I put the old scroll-clamping bug back and the tests did **not** fail on the short penguin book.
  I moved that test to the long Sherlock book and it now fails with the bug (1,763 px drift) and passes without it.
- Friction: Chromium must be installed once per machine (about 100 MB). In my sandbox I installed it in a temp folder
  (`PLAYWRIGHT_BROWSERS_PATH`); on your machine run `uv run playwright install chromium`.

## 2. "Ask about this" tooltip for selected text (done)
- Select text in your question, an answer, a passage or the book reader: a tooltip "Ask about this" appears next to
  the pointer; a click asks `What does the book say about “…”?` (selection cut at 200 characters).
- How: a small invisible component (`selection.js`) listens in the page, uses `event.composedPath()` to see inside the
  reader's shadow root, and sends the text to Python as an event. Question text: `selection.py`.
- Tests: 7 browser tests (answer, own question, passage, book, nothing outside, Escape/click away, plain click) plus
  Python and Node unit tests. Mutation check: breaking the region rule makes 1-2 browser tests fail.
- Friction: Streamlit has no selection events and `st.chat_input` cannot be pre-filled, so the click asks the question
  directly instead of putting it in the input box. Touch and keyboard-only use are not handled (TODO).

