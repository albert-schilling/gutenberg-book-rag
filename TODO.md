# TODO and improvements

Open items, roughly in the order they are worth doing. Numbers refer to the reports in `evals/reports/` and to
`docs/changes.md`. Done items are at the end.

## Evaluation

- [ ] **Human labels for the judge.** Rubric 3 agrees with one annotator (me) on 15 of 17 answers. Label 30 or more answers by hand, and
  measure how often a second run of the judge disagrees with itself.
- [ ] **Hand-written questions** for the test split: multi-fact ("which two enemies..."), comparison ("how does the Emperor differ..."), "how
  many" and whole-book questions. The 51 test questions are one model's drafts (plain words, one fact each); only 3 are about the whole book.
- [ ] **Golden questions for the other seven books.** Only the penguin book is measured; `book-rag-eval` always evaluates the default book.
  Give every book its own set and a `--book` option. Start with a novel (Frankenstein or Oz) and the climate textbook, to see how far the
  penguin results (e5, 1000/200, the soft refusal rule) carry.
- [ ] **A better recall metric.** Evidence phrases are a proxy: a retrieval that finds another passage with the same fact scores 0 (`food` was
  answered correctly with recall 0). Accept several phrases per question, or let a judge decide whether the passages contain the answer.
- [ ] **Run the retrieval evaluation in CI** with the retrieval-only mode (no tokens), and fail when recall drops.
- [ ] Groq: the current setup was only measured on Mistral. Run `BOOK_RAG_LLM=groq uv run book-rag-eval` on a day with tokens left.

## Retrieval and answers

- [ ] **The agent is opt-in** (Settings page, `BOOK_RAG_AGENT=1`, `--agent`). On 51 held-out questions it adds nothing for facts (0.68 against 0.69)
  at 1.7 to 3.2 calls a question; it may help whole-book questions (3 tested). Decide with 20 or more such questions (above).
- [ ] The agent's rewrites are synonyms of the same question ("clutch size", "nest", "typical number"), so retrieval returns the same passages.
  Ask for one query that sounds like a sentence of the book and one with other key words. Only worth it if the agent is kept.
- [ ] HyDE as an option of the agent (a `hypothetical_passage` field; about 30 lines): the best case measured is half a question.
- [ ] **Retrieval is stuck at recall 0.67 to 0.71** (0.71 on dev, 0.67 to 0.69 on test). Ten ideas tried without gain (hybrid, reranker, section
  titles, `mistral-embed`, doc2query, HyDE as a fallback, sentence-level matching, UMAP/HDBSCAN, smaller chunks, larger `k`; see
  `docs/changes.md`). Judge any new idea on the test split.
- [ ] Table of contents: it does not help retrieval, but it is cheap and useful for structure questions ("which part is about skuas?", "which
  story has the speckled band?") and for navigation. Parse the headings per book (like `start` and `end` in `books.py`), add the list to the
  book summary (about 100 to 250 tokens), and offer a chapter jump in the reader.
- [ ] Hybrid search (dense + BM25) is not in the app. It does not help e5, but it makes the original MiniLM competitive (recall 0.65 at 800/133).
  Add it as an option if the assignment's MiniLM has to be used. Check the chunk length in tokens whenever the embedding model changes.
- [ ] Re-test a similarity cutoff with e5 (`MIN_SIMILARITY` is 0.0; e5 similarities lie between 0.7 and 0.9).
- [ ] Groq only: `gpt-oss-20b` sometimes returns an empty reply (the retry hides it). Try a `reasoning_effort` setting.

## Project

- [ ] **A direct visit of `/chat` sometimes renders nothing** (about 2 of 12 loads on a local server: a blank page, or the sidebar without the chat). `/` is
  reliable. Not understood yet (a loaded page with no console error; maybe the machine was busy). The browser tests enter through the start screen and reload a blank page; the screenshots enter the same way.
- [ ] **Check the book summaries by eye.** The penguin summary says "Discovery Expedition" (wrong: it came from a passing mention). They are made
  from 14 excerpts only (about 4,000 tokens, one call per book); fixing it changes the prompt of the whole-book questions, so measure them again afterwards. A map-reduce over the whole book would be better but needs about 25 calls
  per large book.
- [ ] Review follow-ups: the session state of the web app is a set of string keys spread over four files (`book_id`, `histories`, `memories`,
  `visible_exchanges`, `reader`, `selected_text`, `agentic_on`); one small typed helper would make it safe to change. `app/reports.py`
  and `app/views/chat.py` are long top-level scripts: move the table-building and rendering helpers into the package where they can be tested.
- [ ] Type checking: `ty` still reports about 10 findings, mostly Streamlit and colorama typing (the real ones are fixed). Add `ty` or `mypy` to CI.
- [ ] Coverage of `book-rag-eval`'s `main` (the command line and the printing): `rejudge`, `with_retries` and the cases are tested, `main` is not.
- [ ] Run the browser tests (`pytest -m browser`, about 2 min) in CI, and in Firefox and WebKit. Today only Chromium; CI runs lint and the unit tests.
- [ ] Long chats: older answers still draw all four passage expanders. Draw a passage only when its expander is open
  (`st.expander(on_change="rerun")`), or draw the chat in a `st.fragment` so that closing the book does not redraw it.
- [ ] Reader panel: a draggable splitter (needs a custom component; today the panel is 38% of the width or full screen). The panel is a CSS
  fixed-position block (`app/views/chat.css`) because Streamlit has no right sidebar.
- [ ] Selection tooltip: it reacts to the mouse and to Shift + arrow keys. Touch screens (selecting by long press) and keyboard-only use
  (the tooltip cannot be reached with Tab) are not handled.
- [ ] Reader: a search in the book, a jump to a chapter, and remembering the reading position per book. The highlight covers the whole chunk,
  including the 200 characters that overlap the chunk before: highlight only the new part, or the sentences the answer used.
- [ ] Pagination: pages are virtual (2,500 characters). Real page numbers or chapter titles would be better, but the headings differ in every
  book, so they need a rule per book.
- [ ] Review the cleaning of each book by eye. Only the first and last line are checked; poems, tables and footnotes (the climate book has many
  tables) are joined like prose and may produce odd passages.
- [ ] Add a project dictionary for the spell checker, which flags words like `dotenv` and `Groq`.

## Done

- [x] The notebook (now in `assignment/`) has a note at the top that it shows the original approach.
- [x] CI (`.github/workflows/ci.yml`): ruff and the unit tests on every push. Not yet tried on GitHub.
- [x] `book-rag-stores build` pre-builds the vector stores; `book-rag-stores clean` removes stale collections (`chroma_db/` of this checkout has one: `penguins-b237154c`, not removed).
- [x] Larger golden set: 72 questions with a `dev` and a `test` split, whole-book and unanswerable questions, a "By split" table in reports.
- [x] Judge calibration: rubric 3 (key facts ticked, verdict in code), `book-rag-eval --rejudge`, checked against one annotator.
- [x] Over-refusal with `mistral-small`: the soft refusal rule is the default (+0.19 on the held-out questions).
- [x] The agent stops searching when a new search finds nothing closer (3.2 searches on unanswerable questions, was 3 to 5).
- [x] The agent is off by default; a Settings page and `--agent` turn it on.
- [x] Run the evaluation again on the current setup (plain and agent, on Mistral): `docs/changes.md`, "Current performance".
- [x] Questions about the whole book: a book summary is in every prompt, and the test split has whole-book questions.
- [x] Give the chat history to the model: the last 2 exchanges and a rolling summary (retrieval still uses only the current question).
- [x] Live tests (`BOOK_RAG_LIVE=1 uv run pytest -m live`): 7 tests, 3 of 3 runs green on Mistral.
- [x] Browser tests for the reader, the selection tooltip, pagination and the settings (Playwright, 25 tests).
- [x] Stop tuning retrieval on the 17 questions: done by adding the held-out split; retrieval generalises.
