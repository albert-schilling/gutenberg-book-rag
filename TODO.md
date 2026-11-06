# TODO and improvements

Ideas that are not done yet, roughly in the order they are worth doing. The numbers refer to the reports in
`evals/reports/`.

## Evaluation

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

- [ ] Bring the notebook up to date (cleaning, hash ids, e5 embeddings with prefixes, scores), or add a note at
  the top that it shows the original approach. `docs/changes.md` lists the differences.
- [ ] Remove old collections from `chroma_db/`. Each change of the model or the chunking leaves one behind.
- [ ] Add a project dictionary for the spell checker, which flags words like `dotenv` and `Groq`.
