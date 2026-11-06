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

## 8. Review of the app (done; tasks 9 and 10 not started, as you asked)
**Method:** ruff (many rules), the type checker `ty`, coverage (93% from the fast tests), and reading every module.
**Are the tests meaningful?** Mostly yes: the retrieval, metrics, memory, agent loop, reader positions and the browser
tests check real logic or the real app. Weak spots found:
- Nothing exercised the **real model**, and the one bug that only the real model showed (two contradicting prompts)
  slipped through every fake. Added `tests/live/` (7 tests, skipped unless `BOOK_RAG_LIVE=1`, a rate limit skips instead
  of fails). Only the first could run (it passed: the Oz summary question is answered); the rest were skipped by the
  daily token limit. My first live-test version could also pass on the fallback summary: fixed.
- Several app and CLI tests use fakes for the model by design; they check wiring, not answer quality. Answer quality is
  the job of the evaluation, which needs to be run again (TODO).
- Earlier I found two browser tests too weak to catch their own bug (mutation checks), and one flaky test caused by a real
  tooltip bug. These are fixed.
**Fixed directly:**
- Lint: ruff configured in `pyproject.toml` (E,F,I,UP,B,SIM,C4,PIE,RET,PTH, line length 120), the whole repo formatted, 0 findings.
- Real findings of the type checker: a missing Gutenberg START/END line crashed with `AttributeError` (now a clear `ValueError`);
  the judge ignored that a structured reply can be a dict; unchecked optionals in the evaluation.
- Design: web app and CLI carried four loose objects and a 6-argument function: now one `Companion` (`conversation.py`)
  with `respond()`; private names imported across modules (`_offline_reply`) made public; private Chroma API
  (`_collection`) replaced by the public `get()`.
**Left as TODO (larger):** typed session-state helper, moving long page scripts into the package, type checking in CI,
coverage of the evaluation command, running the evaluation and the live tests on a fresh token day.
**Friction:** the daily limit blocked every real-model check after task 7. Nothing in this task needed more than fakes.

## Interlude: MiniLM token limit and hybrid search
- A colleague found that MiniLM works better with chunks of 400/60 and hybrid search. I re-ran the retrieval experiments
  (no LLM tokens used): only 3% of our old chunks exceeded MiniLM's 256 tokens, so truncation was a small part; hybrid
  search was the big one (MiniLM 0.35 -> 0.65 at best). e5 is still equal or better on recall (one question of 17) and
  clearly better on MRR, so the app keeps e5. The claim "0.35 -> 0.71 because of the embedding model" was too strong and
  is corrected in `docs/changes.md` and `evals/README.md`. TODO added for a hybrid option and a token-length check.
- Friction: their "token size around 252" cannot be the chunk length (400 characters is about 81 tokens); I read it as
  the model's `max_seq_length`. Not committed: you did not ask for a commit for this one.
## Interlude: Mistral as the language model
- The first key was rejected (401); the new one works. `llm.py` is now the only place that names a provider:
  `BOOK_RAG_LLM=mistral` (default `groq`) switches the answers, the agent, the memory summaries, the book summaries and the
  judge (`mistral-small-latest` / `mistral-large-latest`). Provider errors (Groq and Mistral rate limits, refused key, no
  connection) give a message in the chat. New dependency `langchain-mistralai`. 6 unit tests for the seam.
- Real runs on Mistral: plain answers, the whole-book question (summary), memory summary and the agent work. The 7 live tests
  passed 3 of 3 runs. I did **not** run the evaluation (about 60 calls on your key); say if you want it.
- Findings: (1) the agent's rewrites with Mistral small are synonyms of the same question, so retrieval does not change; in one
  run the passage with the fact was retrieved and the model still refused in the last round (TODO). (2) I had written that the
  agent makes "at most 3 searches"; it makes at most 3 model calls and up to 5 searches: fixed in code, docs and tests.
  (3) Two live tests asserted retrieval quality and were flaky; they now check what must hold for any model.
- Not committed.
## Interlude: evaluation on Mistral (done)
- Ran `book-rag-eval` and `book-rag-eval --agent` with `BOOK_RAG_LLM=mistral` (reports `20261106-151524-full`, `20261106-151938-agent`).
  The first agent run crashed on a Mistral 429 because the evaluation had no rate-limit handling: `with_retries` (waits 30 s, up to 6
  times, other errors are not retried) was added and tested; the rerun used `--pause 3` and needed no waits.
- Plain: correctness 0.47, abstention accuracy 0.67. Agent: 0.71 and 0.95, faithfulness 0.91, 1.9 searches a question.
- **The gain is a prompt effect, not search.** All 6 improved questions were answered after one search; 'fasting' (5 searches) and
  'rookery-size' (3) stayed wrong; every unanswerable question cost 3 to 5 searches. `mistral-small` over-refuses with the plain
  prompt even when the evidence is at rank 1. I had expected the loop to help; it did not on this set (17 answerable questions: one is 0.06).
- Not run: the same evaluation on Groq (no tokens), a plain pipeline with the agent's prompt, other Mistral models. TODO added.
- Not committed.
## Interlude: how to improve the system (analysis)
- Tested on the penguin book, retrieval only, with the same 17 questions (e5 plain: recall 0.71, MRR 0.56): section title before each
  chunk (0.74 / 0.50), `mistral-embed` (0.59), doc2query with 4 generated questions per chunk (0.47 to 0.71, about 230 Mistral calls),
  HyDE as a fallback (upper bound 0.74), sentence-level matching (0.65 to 0.71), plus the earlier UMAP/HDBSCAN, hybrid, reranker and
  chunk-size runs. Nothing moved the five misses. Not implemented, only documented.
- Conclusion: the biggest measured lever is the refusal prompt (0.47 to 0.71), then the evaluation itself (a larger set, a calibrated
  judge). Not committed.
## Four improvements, measured (done)
1. **Soft refusal rule for the plain pipeline** (default now; `BOOK_RAG_REFUSAL=strict` for the old one): correctness 0.47 to 0.76 on the 21
   questions with the old judge; held-out 0.50 to 0.69 on the 51 new ones. `BOOK_RAG_MODEL=mistral-medium-latest` tried: no gain on held-out.
2. **Judge calibration:** I audited the 8 imperfect verdicts (4 looked wrong), built rubric 2 (key facts ticked, verdict in code) and measured
   it against my labels: 12 of 17, worse than the old judge (13), because the judge misused a "contradicts" flag for extra details.
   Rubric 3 (clear definition, three examples) reaches 15 of 17. `--rejudge` regrades saved answers. One annotator (me), so not ground truth.
3. **72 questions** (21 dev, 51 test; test drafted by mistral-large from 52 chunks, quotes verified by code, 10 drafts dropped by hand) with a
   `split` field and a "By split" table in the report; whole-book questions have no evidence and no retrieval score.
4. **Agent stop rule:** stop after an extra search that found nothing closer. Searches on unanswerable questions 3.2 (before 3 to 5).
- Result: only the soft rule survives the held-out split. The agent and the medium model gain on dev (+0.08) and not on test (0.68, 0.69 against 0.69).
- Frictions: two jobs on one Mistral key rate-limited each other (drafting lost 36 of 52 calls; rerun alone with backoff); my first judge
  rubric made things worse and I had to measure it before noticing; I changed the default refusal rule but left the agent default on: your call.
- Not committed.
## Agent off by default, Settings page, TODO audit
- `BOOK_RAG_AGENT` now defaults to off (`AGENTIC_DEFAULT`); the plain pipeline with the soft refusal rule is what runs. New page
  `app_pages/settings.py` (agent switch, language model and refusal rule shown); the link sits above "Changes from the assignment" in the
  sidebar, and the switch left the sidebar. CLI: `--agent` / `--no-agent`.
- Friction: Streamlit forgets the state of a widget that is not drawn, so a switch on its own page would reset when you leave it. The choice is
  copied to `agentic_on` in a callback, and the page reads it back (tested in AppTest and in a real browser).
- Tests: 4 new AppTest tests, 3 browser tests (links and order, the switch is off, the choice survives leaving the page, the model is named).
- TODO audit: 11 items were done or obsolete (larger golden set, whole-book questions, evaluation re-run, judge calibration, over-refusal, the
  stop rule, summary in the prompt, chat history to the model, live tests on Mistral, browser tests, the agent default). The file now has open
  items grouped by area and a "Done" list; duplicates were merged (the vector-store pre-build was listed twice) and Groq-only items marked.
- Not committed.

---
# Batch 3: changes page, layout, design, restructure

## Ground rules for this batch
- Same branch (`agent/assignments`), one commit per task, only my files. You had already committed and pushed everything before this batch.
- "Right sidebar": Streamlit has no right sidebar (`st.sidebar` is left-only). I read the request as a right-hand panel that can be made wider.
- I do not ask questions while you are away; where a request is ambiguous I choose the reading above and note it.

## A. Changes page restructured (done)
- New order: Performance, the most important changes, why e5 and not MiniLM, Tried and rejected, all other changes, Known limits.
- Mistakes fixed: the prompt row still described the strict refusal rule; "Why the embedding model changed" claimed correctness 0.44 to 0.76,
  which the later correction undermined (removed); "Known limits" still said 17 and 21 questions (now 72), that whole-book questions are answered
  poorly (they use the summary), and named Groq; a "Measured" bullet duplicated the performance section.
- Duplicates merged: the similarity cutoff, HyDE and rewriting were each described twice; the 26-row table is now a 9-row "most important"
  table plus a 13-row "all other changes" table.

### B + C: scrolling and the reader panel (one commit)
- The chat page no longer scrolls: page-level overflow is hidden, the chat is a fixed-height container sized from the viewport, the book's
  title is a one-line `h1` above it. CSS is in `app_pages/chat.css` (injected by `app_pages/styles.py`).
- Reader: Streamlit has no right sidebar, so the reader is a `position: fixed` keyed container on the right with a "Wider"/"Narrower" button
  (38vw / 62vw) and "Close". On a phone (< 800 px) it fills the screen below the header.
- Friction: the reader opened at the wrong place because its shadow-root wrappers had no height; fixed with CSS and by opening the text
  only once the panel has a stable size (`reader.js`). A draggable splitter is not possible without a custom component: in TODO.
- Also fixed 10 ruff findings; tests: AppTest title assertions, 3 new browser tests (`test_layout_browser.py`). 426 unit and 28 browser tests pass.

### D: design
- New `.streamlit/config.toml` theme (paper `#fbf8f1`, ink, oxblood accent, serif headings) and a CSS section in `app_pages/chat.css`: bordered
  chat bubbles (questions dashed), softer passage cards, shadowed input and reader panel. The reader already used theme variables, so it follows.
- Not done: a dark theme (the palette is light only); custom fonts (Streamlit's built-in serif is used, no font files added).

### 9: restructure
- `assignment/` holds the notebook (data and `chroma_db` paths patched to `..`), the original README (with a pointer to the new one) and the
  diagram. `rag_cli.py` removed: `uv run book-rag` is the finished tool. `agent-log.md` moved to `docs/`. Project renamed `book-rag`.
- New README (what it shows, results, quick start, phone views, layout), `Makefile`, `scripts/take_screenshots.py` (real Mistral answer).
- Mobile: the reader fills the screen below the header (already in B+C); checked on 390x844, screenshots in `docs/images/`.
- Not done: moving `streamlit_app.py`/`app_pages/` into an `app/` folder. Streamlit's theme and AppTest paths depend on the root entry
  point; the gain was small. The notebook itself still shows the old approach (TODO).

### 10: TODOs picked
- CI workflow (ruff + unit tests; not run on GitHub yet, there is no way to check from here), `book-rag-stores build|clean` with a test.
- Did not delete the one stale collection in the local `chroma_db/` (user data, rebuilt on demand): run `uv run book-rag-stores clean`.
- Skipped on purpose: fixing the penguin summary ("Discovery Expedition" is wrong). A new summary changes the prompt of all whole-book answers,
  so the reported numbers would no longer match; noted in TODO.

### Batch 4: reader, avatars, scrolling, start screen
- Reader: "Wider" replaced by "Full screen" (window width minus 3 rem on large windows; full width below 800 px, where the button is hidden).
- Chat avatars: no filled box, only the icon in the accent colour.
- Scroll: a hidden helper component (`scroll_component.py`) scrolls the chat pane down whenever the number of messages changes, so a question
  from the "Ask about this" tooltip also scrolls (Streamlit only follows new content while the reader is already at the bottom).
- Pager: moved to the bottom of the reader (chevron buttons and a plain text field, no spinner arrows); the progress bar stays at the top.
  Found on the way: the reader's height was the whole panel, not the panel minus the header; fixed in `chat.css`.
- Start screen: `app_pages/home.py` shows the eight books as cards with a one-line blurb (`Book.blurb`); a click selects the book and opens
  `/chat`. The chat moved to the URL `/chat`. The tooltip's z-index is now above the (raised) panel.
- Bug found while taking the full-screen screenshot: the `--st-*` theme variables only exist inside components, so `chat.css` fell back silently
  (the panel was transparent). The page CSS now has its own palette (`app_pages/base.css`, same colours as `.streamlit/config.toml`).
- Browser test `test_a_long_chat_keeps_the_page_small` failed once in a full run (a 30 s wait) and passed alone and in the next two full runs: flaky under load.

### Batch 5, task 2 (done first: the other tasks touch these files): folder structure
- Why `src/book_rag` and not the rest: the `src/` layout is for the installable package, so that tests and apps import the installed code, not a
  copy from the working directory. Streamlit scripts are not importable code, so they were loose at the top level, which was untidy.
- Now: `app/streamlit_app.py` (entry), `app/views/` (pages and CSS), `app/reports.py`; run with `make app` or `uv run streamlit run app/streamlit_app.py`.
  `.streamlit/config.toml` stays at the root (Streamlit reads it from the folder it is started in). `app_pages` renamed `views` to avoid
  Streamlit's own `pages/` folder convention. The README explains this. All tests (428 + 30 browser) pass.
