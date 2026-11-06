# Evaluation

Measures how well the RAG system retrieves the right passages and answers from them, so changes
(chunk size, `k`, embedding model, prompt, LLM) can be compared with numbers.

```bash
uv run book-rag-eval                    # full run: retrieval + answers + LLM judge (about 55 Groq calls)
uv run book-rag-eval --retrieval-only   # no Groq calls, takes seconds
uv run pytest                           # unit tests and the retrieval regression floor
uv run pytest -m "not integration"      # without the real embedding model
```

```bash
uv run streamlit run streamlit_reports.py   # dashboard: compare two reports, history, per-question details
```

Every run writes `reports/<timestamp>-<mode>.json` (compare runs) and `.md` (read). A report
records the settings (chunking, `k`, models, prompt hash), the Git commit and the dataset hash, so
two reports are only comparable when the dataset hash matches.

## Dataset

`dataset.json` is about the default book (Antarctic Penguins); the other books have no golden questions yet
(see `TODO.md`). It has 17 answerable questions with a reference answer and **evidence phrases** copied
from the cleaned book, and 4 questions the book cannot answer. Evidence phrases, not chunk ids,
keep the dataset valid when the chunking changes. `tests/test_eval_dataset.py` checks that every
phrase is in the book and inside a single chunk.

## Metrics

| Metric | Needs LLM | Meaning |
| :-- | :-: | :-- |
| context_recall | no | Share of the evidence phrases found in the retrieved passages |
| hit_rate | no | Share of questions where at least one evidence phrase was retrieved |
| mrr | no | 1 / rank of the first passage with evidence, averaged |
| context_precision | no | Share of the retrieved passages that contain evidence |
| abstention_accuracy | no | Answerable questions answered, unanswerable ones refused |
| empty_answer_rate | no | Share of questions where the model returned nothing |
| faithfulness | judge | Share of the answer's claims that the retrieved passages support |
| answer_correctness | judge | Agreement with the reference answer (1, 0.5 or 0) |

The judge is `openai/gpt-oss-120b`, a larger model than the generator, so it does not grade its own
answers. It is still an LLM: spot-check its verdicts in the JSON report before trusting a small change.

## Limits

- Context recall is a proxy: it looks for the phrase, so a retrieval that finds another passage with the
  same fact scores 0 (the `fasting` question is answered correctly without its phrase).
- 21 questions are enough to see big changes, not small ones.

## Retrieval experiments (2026-11-06)

Scored with the retrieval metrics on the 17 answerable questions, `k=4`, chunks of 1000/200 unless noted.
Baseline report: `reports/20261106-105714-full.*`; after the change: `reports/20261106-111419-full.*`.

| Variant | Context recall | MRR | Context sent to the LLM |
| :-- | --: | --: | --: |
| all-MiniLM-L6-v2 (the original) | 0.35 | 0.29 | 3,059 chars |
| MiniLM, chunks 500/100 | 0.47 | 0.40 | 1,667 |
| MiniLM, `k=8` | 0.59 | 0.33 | 6,251 |
| MiniLM + BM25 hybrid | 0.65 | 0.39 | 3,173 |
| MiniLM + cross-encoder reranker (top 20) | 0.65 | 0.52 | 2,934 |
| multi-qa-MiniLM-L6-cos-v1 | 0.47 | 0.36 | 3,086 |
| all-mpnet-base-v2 | 0.59 | 0.41 | 3,136 |
| bge-small-en-v1.5 | 0.65 | 0.50 | 3,053 |
| bge-base-en-v1.5 | 0.53 | 0.43 | 2,952 |
| **e5-small-v2 (chosen)** | **0.71** | **0.56** | 3,028 |
| e5-small + BM25 hybrid, or + reranker, or `k=5..6` | 0.65 to 0.71 | 0.51 to 0.56 | no gain |

With 17 questions one question is 0.06, so variants within about 0.1 of each other are ties. What is
robust: every alternative embedding model beats the original MiniLM by 0.12 or more, and the extra
machinery (hybrid, reranker, larger `k`) does not beat a better embedding model on its own. e5-small-v2
was chosen because it is the simplest top variant: same size as MiniLM, no extra model or dependency.

Effect on the full evaluation (same generator and judge):

| Metric | MiniLM | e5-small-v2 |
| :-- | --: | --: |
| context_recall | 0.35 | 0.71 |
| answer_correctness | 0.44 | 0.76 |
| abstention_accuracy | 0.76 | 0.90 |
| faithfulness | 0.98 | 1.00 |

Query rewriting with the LLM (all with e5-small-v2, scored on the same questions; `gpt-oss-20b` wrote the
rewrites, one try per technique):

| Variant | Context recall | MRR |
| :-- | --: | --: |
| Plain question (what is used) | 0.71 | 0.56 |
| Keyword rewrite of the question | 0.44 | 0.35 |
| Rewrite + original question (rank fusion) | 0.62 | 0.50 |
| HyDE (hypothetical answer passage) | 0.44 | 0.37 |
| HyDE + original question (mean of the vectors) | 0.68 | 0.50 |
| Three paraphrases + original (rank fusion) | 0.44 | 0.38 |

Every variant is worse than the plain question. HyDE invented details ("pilfer the freshly laid eggs") that
pulled the search away from the wording of the book, and each variant costs an extra LLM call per question,
so none was adopted.

Still missing (recall 0): `nest-theft`, `fasting`, `food`, `rookery-size`, `enemies`. The right chunk ranks
8th to 57th: the question and the passage use different words ("feed on" vs "feeding on the shrimp-like
euphausia"). Next ideas: rewriting the question with the LLM before retrieval, or a larger golden set to
tell small improvements from noise.

## Correction: the token limit and hybrid search (re-run, retrieval only)

The table above compared MiniLM only with dense search. `all-MiniLM-L6-v2` truncates at 256 tokens; only 3% of our
1000-character chunks were longer (median 169 tokens), but hybrid search (dense + BM25, reciprocal-rank fusion) closes most
of the gap. Same 17 questions, `k=4`:

| Variant | Context recall | MRR |
| :-- | --: | --: |
| MiniLM 1000/200, dense | 0.35 | 0.29 |
| MiniLM 400/60, hybrid (a colleague's setting) | 0.53 | 0.40 |
| MiniLM 500/83 or 600/100, hybrid | 0.59 | 0.47 to 0.48 |
| MiniLM 800/133, hybrid | 0.65 | 0.44 |
| e5 800/133 to 1000/166, dense or hybrid | 0.71 | 0.54 to 0.57 |
| e5 400/60, dense or hybrid | 0.53 | 0.39 to 0.42 |

MiniLM with hybrid and chunks under the token limit is within one question of e5 on recall (0.65 against 0.71) but about
0.1 lower on MRR. One question is 0.06, so only the MRR gap is consistent. e5 stays; the conclusion "e5 doubles recall" was
too strong.

## Plain pipeline against the agent, with Mistral (2026-11-06)

Same 21 questions, `mistral-small-latest` answers, `mistral-large-latest` judges. The book summaries and the memory are in the prompt.
These reports are not comparable with the Groq ones above (other model, other prompt).

| Metric | Plain | Agent |
| :-- | --: | --: |
| context_recall / MRR | 0.71 / 0.56 | 0.71 / 0.56 (same retrieval for the first search) |
| answer_correctness | 0.47 | 0.71 |
| abstention_accuracy | 0.67 | 0.95 |
| answered_when_answerable | 0.59 | 0.94 |
| faithfulness | 1.00 | 0.91 |
| searches_per_question | 1.0 | 1.9 |

The agent fixed 6 questions that the plain pipeline refused **although the evidence was at rank 1** (nest material, eggs, hen on the
nest, sea-leopards, ...), and every one of them needed only one search. The search loop itself rescued nothing. The difference is
the prompt: the plain one tells the model to say "The book does not answer this question" unless the passages do, and
`mistral-small` over-refuses; the agent's does not. Next test: give the plain pipeline the agent's prompt (one call, no loop).

## Bigger question set, held-out split and a calibrated judge (2026-11-06)

`dataset.json` has 72 questions: 21 `dev` (used while tuning) and 51 `test`, which were drafted by `mistral-large` from 52 evenly spaced chunks
of the book (every evidence quote is checked by code against the book; 10 drafts that depended on context were dropped by hand), plus 3
whole-book and 6 unanswerable questions. Reports show a "By split" table. The judge is rubric 3 (key facts ticked by the judge, verdict
computed in code); `book-rag-eval --rejudge report.json` grades the saved answers of an older report again.

| Setup (Mistral small) | Correctness dev / test | Abstention accuracy | Faithfulness | Calls per question |
| :-- | --: | --: | --: | --: |
| Plain, strict refusal rule | 0.53 / 0.50 | 0.61 | 0.96 | 1.0 |
| Plain, soft refusal rule (default) | 0.74 / 0.69 | 0.79 | 0.94 | 1.0 |
| Agent with the stop rule | 0.82 / 0.68 | 0.85 | 0.92 | 1.7 |
| Plain, soft rule, `mistral-medium` | 0.82 / 0.69 | 0.82 | 0.95 | 1.0 |

The soft rule is worth +0.19 on the held-out questions. The agent and the larger model improve the `dev` questions and not the `test` ones:
that gap is what tuning on a small set looks like. Retrieval: recall 0.71 on dev, 0.67 to 0.69 on test, MRR 0.55.
