# TODO and improvements

Ideas that are not done yet, roughly in the order they are worth doing. The numbers refer to the reports in
`evals/reports/`.

## Evaluation

- [ ] **Run the evaluation again** (`uv run book-rag-eval`, then `uv run book-rag-eval --agent`): the last report is from before the
  book summaries, the memory and the agent. One full run is about 60 calls and 100,000 tokens: the free Groq plan allows 200,000
  tokens a day per model, so run them on different days. Then compare the reports in the dashboard.
- [ ] **Golden questions for the other seven books.** Only the penguin book is measured (`evals/dataset.json`).
  The reports record the book, and `book-rag-eval` always evaluates the default book. Give every book its own set
  and a `--book` option, then check whether the embedding model and the chunk size chosen for the penguins also
  suit a novel or a textbook. Start with two more books, a novel (for example Frankenstein or Oz) and the climate
  textbook, to see how far the penguin results carry.
- [ ] **Larger golden set.** 21 questions (17 answerable) can only show big changes: one question is 0.06 of
  recall, so variants within about 0.1 of each other are ties. Aim for 60 to 100 questions, written in different
  styles (short and long, with and without the book's wording, about one fact and about several) and spread
  evenly over the whole book. Split off a part that is never used for tuning, to catch overfitting to the
  questions we looked at.
- [ ] **Better recall metric.** Evidence phrases are a proxy: a retrieval that finds another passage with the same
  fact scores 0 (`fasting` is answered correctly without its phrase). Options: several acceptable phrases per
  question, or a judge that decides whether the retrieved passages contain the answer.
- [ ] **Judge reliability.** Check a sample of judge verdicts by hand and measure how often a second run of the
  judge disagrees.
- [ ] **Whole-book questions** ("What is this book about?", "Summarize the book") need their own questions in
  the set; today they cannot be scored.
- [ ] **Run the evaluation in CI** with the retrieval-only mode, and fail when recall drops.

## Retrieval and answers

- [ ] **Over-refusal with Mistral small.** The plain prompt makes it refuse when the evidence is at rank 1 (6 of 17 answerable
  questions). Test a softer refusal rule for the plain pipeline (the agent's prompt without the loop) and larger models
  (`mistral-medium-latest`), then re-run `book-rag-eval`. If it works, the agent's loop may not be worth its tokens.
- [ ] The agent spends 3 to 5 searches on every unanswerable question and found nothing it missed. Stop after one extra round when
  the new passages are not more similar than the first ones.
- [ ] The agent's rewrites are not diverse: with Mistral small they are synonyms of the same question ("clutch size", "nest",
  "typical number"), so retrieval returns the same passages. Ask for one query that sounds like a sentence of the book, and
  one with other key words. Compare models with `book-rag-eval --agent` once the evaluation can run (see above).
- [ ] Hybrid search (dense + BM25) is not in the app. It does not help e5, but it would make the original MiniLM setup
  competitive (recall 0.65 at 800/133). Add it as an option if the assignment's MiniLM has to be used. Chunk length in
  tokens (not characters) should be checked whenever the embedding model changes (`max_seq_length`).
- [ ] Five questions still find no evidence (`nest-theft`, `fasting`, `food`, `rookery-size`, `enemies`). The
  right chunk ranks 8th to 57th. Ideas not tried yet: chunking by paragraph or sentence, adding the section
  heading to every chunk, a reranker on top of `e5-small-v2`, a larger embedding model with a better set of
  questions to choose it.
- [ ] Questions about the whole book: a short summary of the book in the prompt, or a separate summary chunk.
- [ ] Give the chat history to the model, so follow-up questions ("and why?") work. The page shows the history
  already.
- [ ] Find out why `gpt-oss-20b` sometimes returns an empty reply (the retry only hides it). Try a
  `reasoning_effort` setting or another model.
- [ ] Re-test the similarity cutoff with the e5 model, whose similarity values lie in a different range.

## Project

- [ ] Review follow-ups (larger): the session state of the web app is a set of string keys spread over three files
  (`book_id`, `histories`, `memories`, `visible_exchanges`, `reader`, `selected_text`, `agentic`); one small typed helper
  would make it safe to change. `streamlit_reports.py` and `app_pages/chat.py` are long top-level scripts: move the
  table-building and the rendering helpers into the package where they can be unit-tested.
- [ ] Type checking: `ty` still reports about 10 findings, mostly Streamlit and colorama typing (the real ones are fixed).
  Add `ty` or `mypy` to CI once those are silenced.
- [ ] Coverage of `evaluation/run.py` `main` (64%): the command line and the report printing are only tested by hand.
- [ ] The live tests (`BOOK_RAG_LIVE=1 uv run pytest -m live`) were written but only the first one could run: the daily
  token limit was used up. Run them once on a fresh day.
- [ ] Pagination: pages are virtual. Real page numbers or chapter titles (a table of contents per book) would be better;
  the chapter headings differ in every book, so they need a rule per book (like the start and end lines in `books.py`).
- [ ] Book summaries: made from 14 excerpts only (about 4,000 tokens, one call per book). A map-reduce over the whole book
  would be better but needs about 25 calls (a minute each) per large book on the free Groq plan. Check the summaries by eye.
- [ ] Pre-build the vector stores of all books (a script): the first selection of a book takes 2 to 4 s (spinner "Preparing the book").
- [ ] Long chats: older answers still draw all four passage expanders. Draw a passage only when its expander is open
  (`st.expander(on_change="rerun")`), or draw the chat in a `st.fragment` so that closing the book does not redraw it.
- [ ] Selection tooltip: it reacts to the mouse and to Shift + arrow keys. Touch screens (selecting by long press) and
  keyboard-only use (the tooltip cannot be reached with Tab) are not handled.
- [ ] Run the browser tests (`pytest -m browser`, about 40 s) in CI, and in Firefox and WebKit too. Today only Chromium.
- [ ] Reader: a search in the book, a jump to a chapter, and remembering the reading position per book.
- [ ] Reader: the highlight covers the whole chunk, including the 200 characters that overlap the chunk before.
  Highlight only the part that is new, or the sentences the answer used.
- [ ] Review the cleaning of each book by eye. Only the first and last line are checked. Poems, tables and
  footnotes (Climate has many tables) are joined like prose and may produce odd passages.
- [ ] Build the vector stores of all books in advance (a script), so the first question about a book is not slower.
- [ ] Bring the notebook up to date (cleaning, hash ids, e5 embeddings with prefixes, scores), or add a note at
  the top that it shows the original approach. `docs/changes.md` lists the differences.
- [ ] Remove old collections from `chroma_db/`. Each change of the model, the chunking or the cleaned text leaves one
  behind (today `penguins-b237154c` from before the multi-book change).
- [ ] Add a project dictionary for the spell checker, which flags words like `dotenv` and `Groq`.
