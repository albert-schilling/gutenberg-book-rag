"""Run the evaluation and save a report: `uv run book-rag-eval`."""

import argparse
import time

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from book_rag.config import ENV_FILE
from book_rag.evaluation import judge as judging
from book_rag.evaluation import metrics
from book_rag.evaluation.dataset import EvalCase, load_dataset
from book_rag.evaluation.report import run_metadata, summarize, write_report
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


def evaluate_generation(case: EvalCase, answer: str, scored_passages: ScoredPassages, judge: BaseChatModel) -> dict:
    """Abstention (no LLM), then faithfulness and correctness (LLM judge)."""
    abstained = metrics.is_abstention(answer)
    empty = not answer.strip()  # gpt-oss sometimes returns nothing at all
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
        faithfulness, claims = judging.judge_faithfulness(
            judge, case.question, answer, format_context(scored_passages)
        )
        generation["faithfulness"] = faithfulness
        generation["claims"] = [claim.model_dump() for claim in claims]
    if case.answerable:
        if abstained or empty:
            generation["correctness"] = 0.0
            generation["correctness_reason"] = "The system returned an empty answer." if empty else "The system did not answer."
        else:
            generation["correctness"], generation["correctness_reason"] = judging.judge_correctness(
                judge, case.question, answer, case.reference_answer
            )
    return generation


def evaluate_case(case: EvalCase, vector_store: Chroma, chain: Runnable | None, judge: BaseChatModel | None) -> dict:
    if chain is None:  # retrieval only: no calls to the language model
        answer, scored_passages = None, retrieve(case.question, vector_store)
    else:
        answer, scored_passages = ask(case.question, vector_store, chain)
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
        "answer": answer,
        "generation": None if chain is None else evaluate_generation(case, answer, scored_passages, judge),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate the retrieval and the answers of the RAG system.")
    parser.add_argument("--retrieval-only", action="store_true", help="skip the language models (no Groq calls)")
    parser.add_argument("--limit", type=int, help="only run the first N questions")
    parser.add_argument("--pause", type=float, default=1.0, help="seconds between questions (Groq rate limit)")
    args = parser.parse_args(argv)

    load_dotenv(ENV_FILE)
    vector_store = build_vector_store()
    chain = None if args.retrieval_only else build_chain()
    judge = None if args.retrieval_only else judging.build_judge()
    cases = load_dataset()[: args.limit]

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.id}", flush=True)
        results.append(evaluate_case(case, vector_store, chain, judge))
        if chain is not None and i < len(cases):
            time.sleep(args.pause)

    report = {
        "metadata": run_metadata("retrieval" if args.retrieval_only else "full"),
        "summary": summarize(results),
        "results": results,
    }
    json_path, md_path = write_report(report)

    print("\nSummary:")
    for group, scores in [("retrieval", report["summary"]["retrieval"]), *([("generation", report["summary"]["generation"])] if "generation" in report["summary"] else [])]:
        for name, value in scores.items():
            print(f"  {group:<10} {name:<28} {'n/a' if value is None else f'{value:.2f}'}")
    print(f"\nReport: {md_path}\n        {json_path}")
