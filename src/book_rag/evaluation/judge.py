"""LLM-as-judge metrics. A larger model than the generator grades the answers."""

from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from book_rag.config import JUDGE_MODEL

FAITHFULNESS_PROMPT = """You check whether an answer is supported by the passages it was based on.

Split the answer into short, separate factual claims. For every claim decide whether the passages \
support it (the passages say it or clearly imply it). A claim that is true in general but not stated \
in the passages is NOT supported.

Passages:
{context}

Question: {question}

Answer: {answer}"""

CORRECTNESS_PROMPT = """You compare an answer with a reference answer for the same question.

- correct: the answer states the key facts of the reference answer and does not contradict it.
- partially_correct: it states some of the key facts, or states them with a notable omission.
- incorrect: it misses the key facts, contradicts the reference, or says it cannot answer.

Extra detail in the answer is fine as long as it does not contradict the reference.

Question: {question}

Reference answer: {reference}

Answer: {answer}"""

CORRECTNESS_SCORES = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0}


class Claim(BaseModel):
    claim: str = Field(description="One factual claim from the answer")
    supported: bool = Field(description="True if the passages support the claim")


class FaithfulnessVerdict(BaseModel):
    claims: list[Claim]


class CorrectnessVerdict(BaseModel):
    verdict: Literal["correct", "partially_correct", "incorrect"]
    reason: str = Field(description="One short sentence")


def build_judge() -> BaseChatModel:
    return ChatGroq(model=JUDGE_MODEL, temperature=0, max_retries=6)


def faithfulness_score(claims: list[Claim]) -> float | None:
    """Share of the claims that the passages support (None if the answer makes no claims)."""
    if not claims:
        return None
    return sum(claim.supported for claim in claims) / len(claims)


def judge_faithfulness(judge: BaseChatModel, question: str, answer: str, context: str) -> tuple[float | None, list[Claim]]:
    """Faithfulness: is every claim of the answer supported by the retrieved passages?"""
    prompt = FAITHFULNESS_PROMPT.format(context=context, question=question, answer=answer)
    verdict = judge.with_structured_output(FaithfulnessVerdict).invoke(prompt)
    return faithfulness_score(verdict.claims), verdict.claims


def judge_correctness(judge: BaseChatModel, question: str, answer: str, reference: str) -> tuple[float, str]:
    """Answer correctness: does the answer agree with the reference answer?"""
    prompt = CORRECTNESS_PROMPT.format(question=question, reference=reference, answer=answer)
    verdict = judge.with_structured_output(CorrectnessVerdict).invoke(prompt)
    return CORRECTNESS_SCORES[verdict.verdict], verdict.reason
