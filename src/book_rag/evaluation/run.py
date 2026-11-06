"""Run the evaluation and save a report: `uv run book-rag-eval`."""

import argparse
import time

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from book_rag.agent import agent_ask, build_step_chain
from book_rag.books import DEFAULT_BOOK
from book_rag.config import ENV_FILE
from book_rag.evaluation import judge as judging
from book_rag.evaluation import metrics
from book_rag.evaluation.dataset import EvalCase, load_dataset
from book_rag.evaluation.report import run_metadata, summarize, write_report
from book_rag.llm import PROVIDER_ERRORS, is_rate_limit
from book_rag.rag import ScoredPassages, ask, build_chain, format_context, retrieve
from book_rag.store import build_vector_store


def evaluate_retrieval(case: EvalCase, scored_passages: ScoredPassages) -> dict | None:
    """Retrieval metrics. Unanswerable questions have no evidence, so they have none."""
    if not case.answerable:
        return None
    texts = [passage.page_content for passage, _ in scored_passages]
    return {
        "evidence_found": metrics.evidence_found(case.evidence, texts),
        "context_recall": metrics.context_recall(case.evidence, texts),
        "hit": metrics.hit(case.evidence, texts),
        "reciprocal_rank": metrics.reciprocal_rank(case.evidence, texts),
        "context_precision": metrics.context_precision(case.evidence, texts),
    }


def evaluate_generation(
    case: EvalCase, answer: str, scored_passages: ScoredPassages, judge: BaseChatModel | None
) -> dict:
    """Abstention (no LLM), then faithfulness and correctness (LLM judge)."""
    abstained = metrics.is_abstention(answer)
    empty = metrics.is_empty_answer(answer)  # the model returned nothing, even after the retries of `ask`
    generation = {
        "empty": empty,
        "abstained": abstained,
        "abstention_correct": metrics.abstention_correct(case.answerable, answer),
        "faithfulness": None,
        "claims": [],
        "correctness": None,
        "correctness_reason": None,
    }
    if not (abstained or empty):  # an abstention or an empty answer makes no claims, so there is nothing to check
        assert judge is not None, "a judge is needed to check an answer"
        faithfulness, claims = judging.judge_faithfulness(judge, case.question, answer, format_context(scored_passages))
        generation["faithfulness"] = faithfulness
        generation["claims"] = [claim.model_dump() for claim in claims]
    if case.answerable:
        if abstained or empty:
            generation["correctness"] = 0.0
            generation["correctness_reason"] = (
                "The system returned an empty answer." if empty else "The system did not answer."
            )
        else:
            assert judge is not None and case.reference_answer is not None
            generation["correctness"], generation["correctness_reason"] = judging.judge_correctness(
                judge, case.question, answer, case.reference_answer
            )
    return generation


def evaluate_case(
    case: EvalCase,
    vector_store: Chroma,
    chain: Runnable | None,
    judge: BaseChatModel | None,
    step_chain: Runnable | None = None,
) -> dict:
    """Evaluate one question: with the agent (`step_chain`), with the plain chain, or retrieval only (neither)."""
    queries = [case.question]
    if step_chain is not None:  # the agent may search the book again
        found = agent_ask(case.question, vector_store, step_chain)
        answer, scored_passages, queries = found.answer, found.passages, found.queries
    elif chain is None:  # retrieval only: no calls to the language model
        answer, scored_passages = None, retrieve(case.question, vector_store)
    else:
        answer, scored_passages = ask(case.question, vector_store, chain)
    generates = chain is not None or step_chain is not None
    return {
        "id": case.id,
        "question": case.question,
        "answerable": case.answerable,
        "reference_answer": case.reference_answer,
        "evidence": list(case.evidence),
        "retrieved": [
            {"start_index": p.metadata["start_index"], "similarity": round(s, 4), "preview": p.page_content[:200]}
            for p, s in scored_passages
        ],
        "retrieval": evaluate_retrieval(case, scored_passages),
        "queries": queries,
        "answer": answer,
        "generation": evaluate_generation(case, answer, scored_passages, judge) if generates else None,
    }


def with_retries(call, *, attempts: int = 6, wait: float = 30.0):
    """Run `call`. A rate limit of the language model is waited out instead of ending a long run."""
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except PROVIDER_ERRORS as error:
            if not is_rate_limit(error) or attempt == attempts:
                raise
            print(f"  rate limit, waiting {wait:.0f}s (attempt {attempt} of {attempts})", flush=True)
            time.sleep(wait)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate the retrieval and the answers of the RAG system.")
    parser.add_argument("--retrieval-only", action="store_true", help="skip the language models (no Groq calls)")
    parser.add_argument("--agent", action="store_true", help="let the model search the book again (see agent.py)")
    parser.add_argument("--limit", type=int, help="only run the first N questions")
    parser.add_argument("--pause", type=float, default=1.0, help="seconds between questions (Groq rate limit)")
    args = parser.parse_args(argv)

    load_dotenv(ENV_FILE)
    vector_store = build_vector_store(DEFAULT_BOOK)  # the golden questions are about this book
    chain = None if args.retrieval_only or args.agent else build_chain(DEFAULT_BOOK)
    step_chain = build_step_chain(DEFAULT_BOOK) if args.agent and not args.retrieval_only else None
    judge = None if args.retrieval_only else judging.build_judge()
    cases = load_dataset()[: args.limit]

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.id}", flush=True)
        results.append(with_retries(lambda: evaluate_case(case, vector_store, chain, judge, step_chain)))
        if (chain is not None or step_chain is not None) and i < len(cases):
            time.sleep(args.pause)

    report = {
        "metadata": run_metadata("retrieval" if args.retrieval_only else "agent" if args.agent else "full"),
        "summary": summarize(results),
        "results": results,
    }
    json_path, md_path = write_report(report)

    print("\nSummary:")
    for group, scores in [
        ("retrieval", report["summary"]["retrieval"]),
        *([("generation", report["summary"]["generation"])] if "generation" in report["summary"] else []),
    ]:
        for name, value in scores.items():
            print(f"  {group:<10} {name:<28} {'n/a' if value is None else f'{value:.2f}'}")
    print(f"\nReport: {md_path}\n        {json_path}")
