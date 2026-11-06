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

## 3. Virtualization and performance (done)
- **Can Streamlit virtualize?** Not in general. Only `st.dataframe` and charts render lazily; `st.container(height=...)`
  scrolls but still builds every child. So: the book reader virtualizes itself in the browser (a window of at most 250
  paragraphs, checked by the browser tests), and the chat now draws only the latest 10 questions and answers, with a
  "Show earlier questions" button.
- Measured (offline mode, real browser): without the cap the page grew linearly, 415 -> 8,298 DOM elements after 60
  questions, rerun time 0.14 -> 0.29 s. With the cap it stays at about 1,630 elements and 0.21 s. With the real LLM the
  model call (seconds) dominates anyway.
- Scrolling the longest book: 450,000 px scrolled, 246 paragraphs in the page, 314 DOM elements.
- Tests: 4 app tests for the cap and "Show earlier", 1 browser test for the DOM size.
- **Friction / false lead:** I first measured 2.8-3.8 s to open the big books and blamed the 600 KB sent to the
  browser. I built a static-file delivery (config file, static folder) to fix it. A fair measurement showed that the time
  was the vector store being built the first time a book is selected; the reader opens in 0.2 s either way. I reverted
  the static-file change (more moving parts, no gain). The first selection of a book still takes 2-4 s (TODO: pre-build).

- **Slip, fixed in the next commit:** commit `4f77550` (task 3) was made while one browser test was failing, because my
  command took the exit status of `tail` instead of `pytest`. The failing test showed a real bug: the selection
  tooltip hid itself on the scroll that often follows a selection (so the user could not click it). Fixed with a short
  grace period (`selection.js`), test helper made precise, 6 of 6 reruns green. From now on commits are gated on pytest's exit status.

## 4. Chat memory: summary and rolling window (done)
- `memory.py`: the last 2 question/answer pairs word for word (answers cut to 400 characters), older pairs folded into a
  rolling summary of at most 80 words. It is added to every LLM call as `{conversation}` in the prompt, only to
  understand follow-ups. One memory per book, kept in the session. Error replies are not remembered.
- Token budget (free Groq plan: 8,000 tokens/minute): about 350 extra tokens per call. The summary costs one small extra
  call only when an exchange leaves the window, and a crude fallback keeps the chat working if that call fails.
- Checked with the real model: "Do they also attack the adults?" after a question about skuas was understood.
- Tests: 7 memory unit tests, 2 prompt tests, 3 app tests (the model sees the last 2 exchanges and the summary; one memory per book).
- Friction: retrieval still searches with the current question only, so "Why do they do that?" got a refusal. The agent
  of task 7 rewrites follow-up questions into standalone ones. `st.chat_input` cannot be pre-filled, which does not matter here.

## 5. Book summaries for "What is this book about?" (done)
- Problem: no single passage is about the whole book, so retrieval cannot answer it. Fix: a ~200-word summary of every
  book (`data/summaries/<book>.md`) is part of every prompt (about 300 tokens).
- How the summaries are made (`uv run book-rag-summarize`): a book is 40,000-145,000 tokens but the free plan allows
  8,000 tokens a minute, so a map-reduce over the whole book (about 25 calls of a minute each per big book) was not
  sensible. Instead: 14 evenly spaced excerpts (opening, 12 places with their position, ending; about 4,000 tokens) and
  **one call per book** with `gpt-oss-120b` (`reasoning_effort=low`): 8 calls and about 35,000 tokens in total, with a
  65 s pause between books. The reply is cut after the last complete sentence within 210 words because the model
  ignored the word limit (265 words for Frankenstein).
- Tests: excerpt sampling for all 8 books (size, order, from the book), loading, prompt placement and brace escaping,
  the command with a fake model, the word limit.
- Limits / friction: only 14 excerpts, so details between them are missing; the model sometimes adds facts that are
  not in the excerpts (it knows the famous books). The summaries should be read by a person (TODO).

## 6. Pagination together with the infinite scrolling (done)
- Yes, it works. Pages are **virtual**: 2,500 characters (about 400 words) each, counted in the cleaned text, because
  the text files have no real pages (64 pages for the penguin book, 230 for Tom Brown).
- A bar above the text shows "Page N of M" and a progress bar. The page is that of the text on a reading line a quarter
  down from the top and follows the scrolling in both directions. The page number can be edited: a jump needs no
  server round trip (the browser has all paragraphs) and goes to the first paragraph that starts on that page. A small
  "PAGE N" marker starts every page inside the text. Passages in the chat name their page and open on that page.
- Works with the window of at most 250 paragraphs: markers and page numbers come from the position of a paragraph, not
  from the DOM, so loading and dropping paragraphs does not change them; jumps keep the steady-scroll behaviour.
- Tests: 8 browser tests (indicator, markers, follows scrolling down and up against the markers, progress, jump,
  clamping, scrolling after a jump, a passage opens on its labelled page), JS helper tests, 3 Python tests.
- Friction: my first scrolling test picked markers from the middle of the loaded window and never advanced
  (test bug). Two helper modules named `helpers.py` clashed; the browser one is now `browser_helpers.py`.

## 7. Agentic LLM (done, evaluation not run)
- `agent.py`: the model reads the retrieved passages and either answers or proposes up to 2 new search queries
  (rephrased, standalone, other words). At most 3 searches per question. **The only tool is a search in this book**:
  no web search, no other tool. A question that the first passages answer costs one call, as before. The result
  returns the answer, the merged passages and every search that was made; the chat shows "Searched the book for: ..."
  under the answer. My reading of the cut-off sentence in the task: "return the answer with the questions it used".
- `conversation.respond()`: one turn for the web app and the CLI (agent or plain, memory update). A rate limit or a
  connection error of Groq gives a message ("The free Groq plan is at its limit for now. Please try again in 6m47s.")
  instead of a traceback and is not remembered. Sidebar switch "Search again when needed"; CLI `--no-agent`;
  `BOOK_RAG_AGENT=0` for the default.
- Tests with a scripted fake model: answers at once, searches again, stops after the last round, drops repeated/blank
  queries, merges passages, refuses only in the last round, error messages, UI (switch, searches line, rate limit).
- **Friction 1: the daily token limit.** Besides 8,000 tokens/minute there is a limit of **200,000 tokens per day** per
  model. I used it up (198,608 used) while testing, so I could not run the evaluation for the agent. It needs about
  100,000 tokens: run `uv run book-rag-eval` and `uv run book-rag-eval --agent` on different days (TODO).
- **Friction 2: a prompt conflict** found with the real model: the base prompt said "refuse if the passages do not
  answer", the agent prompt said "search again": the model refused. The refusal rule is now a placeholder that the
  agent replaces. Afterwards it searched again (4 new queries on a fact that retrieval never finds, 117 s with the rate limit).
- Real-model observations (few calls): with the book summary in the prompt the plain pipeline already answers the old
  misses (krill, eggs, enemies); the agent rarely needs a second search.

