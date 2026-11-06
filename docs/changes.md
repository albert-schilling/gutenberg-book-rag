This app started as the book RAG assignment and departs from it in a number of places. This page lists the results first, then the most
important changes, the experiments, and at the end every smaller difference. The notebook (now in `assignment/`) still shows the original approach.

## Performance

Penguin book, **72 questions**: 21 `dev` (used while the system was tuned) and 51 `test` (written later, never used for tuning: 42 facts, 3 about
the whole book, 6 that the book cannot answer). `mistral-small-latest` answers, `mistral-large-latest` judges, `e5-small-v2` embeddings, chunks of
1000/200 characters, 4 passages, book summary and chat memory in the prompt. One test question is worth 0.02, one dev question 0.06.

| Setup | Correctness, facts dev / **test** | Whole-book (3) | Abstention accuracy | Faithfulness | Calls per question |
| :-- | --: | --: | --: | --: | --: |
| Plain, strict refusal rule (the old prompt) | 0.53 / 0.50 | 0.50 | 0.61 | 0.96 | 1.0 |
| **Plain, soft refusal rule (the default)** | **0.74 / 0.69** | 0.50 | 0.79 | 0.94 | 1.0 |
| Agent (searches again; stops when nothing gets closer) | 0.82 / 0.68 | 0.83 | 0.85 | 0.92 | 1.7 (3.2 if unanswerable) |
| Plain, soft rule, `mistral-medium` | 0.82 / 0.69 | 0.67 | 0.82 | 0.95 | 1.0 |

Retrieval is the same in every row: context recall 0.71 on dev and 0.67 to 0.69 on test, MRR 0.55. All 6 unanswerable questions are refused in
every setup. Reports: `evals/reports/`; the metrics are explained in `evals/README.md`.

- **The soft refusal rule is the real gain** (+0.19 on the held-out questions). The strict rule makes `mistral-small` refuse when the evidence
  is at rank 1. It costs nothing, so it is the default.
- **The agent adds nothing measurable for facts it was not tuned on** (0.68 against 0.69: better on 5, worse on 3, same on 37 test questions) and
  costs 1.7 to 3.2 times the calls. Its +0.08 on the dev questions is what tuning looks like. It may help whole-book questions (0.83 against
  0.50), but that is 3 questions. A larger model does not help on the test split either. So the agent is off by default (Settings page).
- **Retrieval generalises**: recall 0.67 to 0.69 on the test split against 0.71 on dev.
- **The judge** (rubric 3) makes the model list the key facts of the reference and tick which the answer states; the score follows from the ticks,
  in code, so extra detail cannot lower it. It agrees with one annotator on 15 of 17 answers (the first judge: 13 of 17) and gives the same saved
  answers 0.82 instead of 0.71. One annotator is not ground truth: human labels are a TODO.

## The most important changes

| Change | Assignment / notebook | This app | Why |
| :-- | :-- | :-- | :-- |
| Embedding model | `all-MiniLM-L6-v2` | `intfloat/e5-small-v2` with `query:` and `passage:` prefixes | Higher MRR (0.56 against 0.29 to 0.47) and no hybrid search needed. See "Why e5" below |
| Refusal rule | answer only from the passages | answer whenever the passages contain the information, even in part; refuse with one exact sentence only when nothing is relevant | +0.19 correctness on held-out questions: the strict rule made the model refuse with the answer at rank 1 |
| Whole-book questions | "What is this book about?" gets a refusal | a 200-word summary of every book is in every prompt (`uv run book-rag-summarize`, `data/summaries/`) | No single passage is about the whole book. Made once from 14 evenly spaced excerpts, one call per book |
| Chat memory | none | the last 2 exchanges word for word, older ones as a rolling summary of at most 80 words, in every call | Follow-up questions ("and why?") can be understood. Retrieval still uses only the current question |
| Evaluation | none | 72 questions with a held-out split, retrieval and answer metrics, an LLM judge, reports and a dashboard | Without it every change was a guess; the held-out split showed which gains were real |
| Agent | one retrieval, one answer | **off by default**; the Settings page (`BOOK_RAG_AGENT=1`, `--agent`) lets the model rephrase the question and search again: at most 3 calls and 5 searches, stops when a search finds nothing closer, only this book (no web search, no other tool) | Measured as above: no gain for facts at 1.7 to 3.2 times the calls |
| Books | one book per group | all eight books, chosen in the sidebar; one Chroma collection per book, built the first time a book is opened | One app serves the whole library; books never mix |
| Reading the source | the `start_index` of each passage | "Read in the book" opens the text in a panel on the right (a button makes it full screen, leaving a thin strip of the page visible; on a phone it always fills the screen) at the passage, highlighted, with a progress bar at the top, a pager at the bottom (back and forward buttons and a page field: "Page 12 of 64"), page markers and a jump to any page | A reader can check an answer in context and keep reading. Pages are virtual (2,500 characters): the files have no real pages |
| Language model | Groq `gpt-oss-20b` | Mistral by default (`mistral-small-latest` answers, `mistral-large-latest` judges); `BOOK_RAG_LLM=groq` switches back | The free Groq plan allows 200,000 tokens a day. `llm.py` is the only module that names a provider |

## Why e5 and not MiniLM

We scored more than 25 retrieval variants on the 17 dev questions (no LLM involved). Context recall is the share of the evidence phrases found in
the 4 retrieved passages.

| Variant | Context recall | MRR |
| :-- | --: | --: |
| `all-MiniLM-L6-v2`, 1000/200, dense (the assignment) | 0.35 | 0.29 |
| MiniLM, 400/60, hybrid (a colleague's setting) | 0.53 | 0.40 |
| MiniLM, 800/133, hybrid (best MiniLM variant) | 0.65 | 0.44 |
| MiniLM + cross-encoder reranker | 0.65 | 0.52 |
| `bge-small-en-v1.5` | 0.65 | 0.50 |
| **`e5-small-v2`, 1000/200, dense (chosen)** | **0.71** | **0.56** |

MiniLM cuts its input at **256 tokens**, but only 3% of the 1000-character chunks were longer (median 169 tokens), so truncation was a small part of
its gap. Most of it was missing **hybrid search** (BM25 and dense, fused by rank: +0.12 to +0.24; for e5 it adds nothing). On recall e5 and the
best MiniLM variant differ by one question of 17: a tie. e5 is ahead on MRR (0.54 to 0.57 against 0.44 to 0.48) and needs no BM25 code, so it stays.
For the original assignment (MiniLM) use chunks of at most about 800 characters and hybrid search.

## Tried and rejected

All on the penguin book with the 17 dev questions (plain e5 search: recall 0.71, MRR 0.56). None moved the five that miss (`nest-theft`, `fasting`,
`food`, `rookery-size`, `enemies`): the missing facts sit in paragraphs about something else (the rookery size is in a paragraph about mating),
and the question uses other words than the book ("feed on" against "feeding on the shrimp-like euphausia").

- **A similarity cutoff.** Questions about the whole book scored the same as unrelated ones (0.33 and 0.34 with MiniLM), so any cutoff drops
  legitimate questions or keeps nonsense. The refusal rule handles it.
- **Rewriting the question with the LLM:** a keyword rewrite, a hypothetical answer (HyDE) and three paraphrases all scored lower than the plain
  question (0.38 to 0.68). HyDE as a second search only where the first failed: 0.74 at best, and only if the agent always knew when (it rescued 1
  of 5; the text invents facts).
- **Clustering** (UMAP and HDBSCAN on the chunk vectors) to route the question, fill the passages from the best hit's cluster or boost that
  cluster: 0.29 for routing, 0.65 for the others. The book is topically uniform (16 clusters with 29% noise, or 2 clusters). t-SNE is for plots only.
- **The section title before every chunk**, as a table of contents would give it: 0.74 recall but MRR 0.50 (all 40 chunks of a part share the title).
- **`mistral-embed`** (0.59, and 0.41 with the titles), **indexing 4 LLM-written questions per chunk** ("doc2query", 0.47 to 0.71), **matching
  single sentences** but returning the whole chunk (0.65 to 0.71), **more passages** (`k` of 5 or 6 does not help e5).

## All other changes

| Area | Assignment / notebook | This app |
| :-- | :-- | :-- |
| Chunking | free choice | 1000 characters, overlap 200 (unchanged: smaller chunks only helped MiniLM) |
| Chroma ids | `f"{BOOK}-{i}"` | SHA-1 hash of the chunk text: the id changes exactly when the text changes |
| Vector stores | none | `book-rag-stores build` (all books) and `clean` (collections that no book uses any more) |
| Building the store | `add_documents` | only if empty; the collection name carries a fingerprint of the model, chunk settings and cleaned text, so a change builds a fresh collection |
| Cleaning | text between START and END, wrapped lines joined | also drops front matter (ads, contents, prefaces), back matter (printer's line, the climate book's index), `[Illustration]` and indentation; the first and last line of each book are in `books.py` |
| Passages | `as_retriever(k=4)` | `similarity_search_with_score`, `k=4`; the cosine similarity (1 - distance / 2 for unit vectors) is shown per passage |
| Empty model replies | not handled | asked again up to 2 more times, then a fallback message (`gpt-oss` sometimes returns nothing) |
| Rate limits and errors | a traceback | a message in the chat; the evaluation waits out a rate limit |
| Asking about a text | one typed question | select text in a question, an answer, a passage or the book, then click "Ask about this" |
| Long chats | the whole history is drawn | the latest 10 exchanges; "Show earlier questions" adds 10 (Streamlit draws every element it is given: 8,300 elements after 60 questions without the cap, about 1,600 with it) |
| Design | Streamlit defaults | a library look: pale grey paper, ink text, one oxblood accent, serif headings and book text (`.streamlit/config.toml`, `app/views/chat.css`) |
| Start screen | a fixed book per group | the first page lists the eight books; a click opens the chat of that book |
| Page layout | one scrolling page | the chat page never scrolls as a whole: the book's title stays at the top, the chat and the book scroll inside their own areas |
| Settings page | none | the agent switch and the language model in use |
| Command line | loop until `quit` | `quit` or `exit`, `--book`, `--agent`; shares one `Companion` object with the web app |
| Offline mode | needs a key | `BOOK_RAG_OFFLINE=1` replaces the language model by a fixed reply: no key, no cost, no rate limit |
| Tests | none | unit, app, browser (Playwright: scrolling, highlight, tooltip, pages, settings) and live tests (`BOOK_RAG_LIVE=1 uv run pytest -m live`) |
| Folder structure | notebook and script at the top level | the package is `src/book_rag` (installed, no Streamlit); the apps are in `app/` (`streamlit_app.py`, `views/`, `reports.py`); the assignment is in `assignment/` |
| Code quality | none | ruff in `pyproject.toml`, `src/book_rag` package, a Makefile, a README with screenshots; the notebook and the assignment text moved to `assignment/` |

## Known limits

- **Only the penguin book is measured.** The model, chunk size and prompt were chosen on its questions. The other seven books only have a smoke test
  (an obvious question finds the right passage).
- 72 questions show big changes, not small ones. The test split comes from one model's drafts (plain words, one fact each) and has only 3
  whole-book questions.
- Whole-book questions are answered from the summary and score 0.50 with the plain pipeline (3 questions): the summary is made from 14 excerpts.
- The memory is small on purpose (the free plans limit tokens per minute and per day), and retrieval ignores it, so "and why?" finds passages poorly.
- Earlier numbers (Groq with the old prompt, the first Mistral reports, the first judge) are not comparable with the table above.
