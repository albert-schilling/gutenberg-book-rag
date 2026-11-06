# Evaluation

Measures how well the RAG system retrieves the right passages and answers from them, so changes
(chunk size, `k`, embedding model, prompt, LLM) can be compared with numbers.

```bash
uv run book-rag-eval                    # full run: retrieval + answers + LLM judge (about 55 Groq calls)
uv run book-rag-eval --retrieval-only   # no Groq calls, takes seconds
uv run pytest                           # unit tests and the retrieval regression floor
uv run pytest -m "not integration"      # without the real embedding model
```

Every run writes `reports/<timestamp>-<mode>.json` (compare runs) and `.md` (read). A report
records the settings (chunking, `k`, models, prompt hash), the Git commit and the dataset hash, so
two reports are only comparable when the dataset hash matches.

## Dataset

`dataset.json` has 17 answerable questions with a reference answer and **evidence phrases** copied
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
