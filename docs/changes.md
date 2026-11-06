This app started as the book RAG assignment and then departed from it in a number of places. Every row below
is a deliberate change, with the reason. The notebook still shows the original approach.

## Overview

| Area | Assignment / notebook | This app | Why |
| :-- | :-- | :-- | :-- |
| Books | one book per group | all eight books, chosen in the sidebar | One app serves the whole library |
| Vector store | one collection | one collection per book, all in `chroma_db/`; built the first time a book is opened | Books never mix, each rebuilds on its own, and nothing is embedded that nobody asks for |
| Embedding model | `all-MiniLM-L6-v2` | `intfloat/e5-small-v2`, with `query:` and `passage:` prefixes | Answer correctness rose from 0.44 to 0.76 (details below) |
| Chunking | free choice | 1000 characters, 200 overlap (unchanged) | Smaller chunks only helped the old model |
| Chroma ids | `f"{BOOK}-{i}"` | SHA-1 hash of the chunk text | The id changes exactly when the text changes, so no stale or duplicate chunks |
| Building the store | `add_documents` | only if the store is empty; the collection name carries a fingerprint of the model and chunk settings | The book is not embedded again on every start, and a changed setting builds a fresh collection instead of reusing old vectors |
| Cleaning | text between START and END, wrapped lines joined | also removes the front matter (ads, title page, contents, prefaces), the back matter (printer's line, the index of the climate book), `[Illustration]` placeholders and paragraph indentation; the first and last line of each book are set in `books.py` | None of this is the book, and it would otherwise be retrieved as a passage |
| Passages | `as_retriever(k=4)` | `similarity_search_with_score`, `k=4`, with the cosine similarity shown per passage | Readers can see how close each passage is. Cosine similarity = 1 - distance / 2 for vectors of length 1 |
| Checking an answer | the `start_index` of each passage | "Read in the book" opens the text next to the chat, at the passage, highlighted, with the text before and after; "Read the book" in the sidebar opens it from the start | A reader can check an answer in its context, and keep reading. The text loads while you scroll, up and down |
| Similarity cutoff | none | none (tried, dropped) | See below |
| Empty model replies | not handled | asked again up to 2 more times, then a fallback message | `gpt-oss-20b` sometimes returns nothing at all |
| Prompt | answer only from the passages | names the chosen book, and demands one exact sentence when the book has no answer | Lets the system and the evaluation recognise a refusal |
| Command line | loop until `quit` | `quit` or `exit` (also Ctrl+C and Ctrl+D), and `--book` to choose the book | An exit word is never sent to the model as a question |
| Code | notebook and `rag_cli.py` | `src/book_rag` package, tests, evaluation, this web app | The CLI and the web apps share the same code |
| Web app | none | wide two-pane layout: chat on the left, the book on the right when a passage is open; a custom component for the book | Reading a passage in its context needs scrolling that the built-in elements do not offer |
| Tests | none | unit tests, app tests, and browser tests with Playwright (headless Chromium) | Infinite scrolling, the steady reading position and the highlight only exist in a real browser. A browser test failed on a scroll-jump bug that no other test saw |
| Offline mode | needs a Groq key | `BOOK_RAG_OFFLINE=1` replaces the language model by a fixed reply (retrieval still runs) | Lets the app be tried and tested without a key, without cost and without the rate limit |

## Why the embedding model changed

We scored more than 25 retrieval variants on 17 questions with known evidence in the book (no LLM involved). Context recall is the
share of the evidence phrases found in the 4 retrieved passages.

| Variant | Context recall | MRR |
| :-- | --: | --: |
| `all-MiniLM-L6-v2` (the assignment) | 0.35 | 0.29 |
| MiniLM with chunks of 500 characters | 0.47 | 0.40 |
| MiniLM + keyword search (BM25) | 0.65 | 0.39 |
| MiniLM + cross-encoder reranker | 0.65 | 0.52 |
| `bge-small-en-v1.5` | 0.65 | 0.50 |
| **`e5-small-v2` (chosen)** | **0.71** | **0.56** |

With the full pipeline (same generator and judge), the change moved answer correctness from 0.44 to 0.76,
abstention accuracy from 0.76 to 0.90 and faithfulness from 0.98 to 1.00. `e5-small-v2` has the same size as
MiniLM, so it needs no extra model or dependency. The reranker and keyword search did not beat a better
embedding model on their own.

## Tried and rejected

- **Similarity cutoff.** With MiniLM, questions about the whole book ("What is this book about?", best similarity
  0.33) scored the same as unrelated ones ("Tell me about elephants", 0.34), so any cutoff either drops legitimate
  questions or keeps nonsense. The prompt already makes the model refuse when the passages do not help.
- **Rewriting the question with the LLM.** A keyword rewrite, a hypothetical answer (HyDE) and three paraphrases
  all scored lower than the plain question (recall 0.38 to 0.68 against 0.71). The model invented details and
  drifted away from the wording of the book, and every variant adds an LLM call per question.
- **More passages.** Raising `k` to 5 or 6 did not help `e5-small-v2` (it did help MiniLM, from 0.35 to 0.59 at `k=8`, but sends 2 times more text to the model).

## Known limits

- **Only the penguin book was measured.** The embedding model, the chunk size and the prompt were chosen on 17
  questions about the penguin book. The other seven books have a smoke test (an obvious question finds the right
  passage) but no golden questions, so their quality is unknown.
- The evaluation has 21 questions: it shows big changes, not small ones. One question is worth 0.06 of recall.
- Five questions still find no evidence, because the question and the book use different words ("feed on" and
  "feeding on the shrimp-like euphausia").
- Questions about the whole book ("Summarize the book") are answered poorly: no single passage is about the whole book.
- Each question is answered on its own: the chat history is shown but not given to the model.

The numbers come from the reports in `evals/reports/`; `evals/README.md` explains the metrics, and
`TODO.md` lists what is planned next.
