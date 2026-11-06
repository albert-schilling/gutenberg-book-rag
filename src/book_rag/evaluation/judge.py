"""LLM-as-judge metrics. A larger model than the generator grades the answers."""

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from book_rag.config import JUDGE_MODEL
from book_rag.llm import build_llm

FAITHFULNESS_PROMPT = """You check whether an answer is supported by the passages it was based on.

Split the answer into short, separate factual claims. For every claim decide whether the passages \
support it (the passages say it or clearly imply it). A claim that is true in general but not stated \
in the passages is NOT supported.

Passages:
{context}

Question: {question}

Answer: {answer}"""

RUBRIC_VERSION = (
    3  # 1: one verdict, extra detail was penalised. 2: key facts, but "contradicts" was misused. 3: see below
)

CORRECTNESS_PROMPT = """You check an answer against the reference answer for the same question.

1. Key facts: the facts that the reference answer needs in order to answer the question, usually one or two. Background
   (who the people were, where something happened) is not a key fact.
2. For each key fact, say whether the answer states it, in the same or other words, or in a more specific form
   (for example "pieces of quartz" for "stones" is the same fact).
3. Says_the_opposite: true ONLY if the answer gives a different value for a key fact: another number, another person, the
   opposite. An extra detail that the reference does not mention is never a difference, so it is never true.

Do NOT take points off for extra details in the answer that the reference does not mention: another check looks at those.

Examples (question, reference, answer -> judgement):
- "Where do they get the stones?", "From old nests.", "They take them from old nests or steal them from neighbours."
  -> key fact "from old nests": stated. Says the opposite: false (the stealing is an extra detail). All stated.
- "How many birds?", "About 750,000.", "Several thousand."
  -> key fact "about 750,000": not stated. Says the opposite: true (a very different number).
- "Which enemies?", "Skuas and sea-leopards.", "Sea-leopards."
  -> key facts "skuas", "sea-leopards": only the second is stated. Says the opposite: false. Partly stated.

Question: {question}

Reference answer: {reference}

Answer: {answer}"""


class Claim(BaseModel):
    claim: str = Field(description="One factual claim from the answer")
    supported: bool = Field(description="True if the passages support the claim")


class FaithfulnessVerdict(BaseModel):
    claims: list[Claim]


class KeyFact(BaseModel):
    fact: str = Field(description="A key fact of the reference answer")
    stated: bool = Field(description="True if the answer states it")


class CorrectnessVerdict(BaseModel):
    key_facts: list[KeyFact]
    says_the_opposite: bool = Field(description="True only if the answer gives a different value for a key fact")
    reason: str = Field(description="One short sentence")


def build_judge() -> BaseChatModel:
    return build_llm(JUDGE_MODEL, max_retries=6)


def faithfulness_score(claims: list[Claim]) -> float | None:
    """Share of the claims that the passages support (None if the answer makes no claims)."""
    if not claims:
        return None
    return sum(claim.supported for claim in claims) / len(claims)


def judge_faithfulness(
    judge: BaseChatModel, question: str, answer: str, context: str
) -> tuple[float | None, list[Claim]]:
    """Faithfulness: is every claim of the answer supported by the retrieved passages?"""
    prompt = FAITHFULNESS_PROMPT.format(context=context, question=question, answer=answer)
    verdict = FaithfulnessVerdict.model_validate(judge.with_structured_output(FaithfulnessVerdict).invoke(prompt))
    return faithfulness_score(verdict.claims), verdict.claims


def correctness_score(verdict: CorrectnessVerdict) -> float:
    """All key facts stated: 1. Some: 0.5. None, or a different value for one: 0. Extra details never lower the score."""
    if verdict.says_the_opposite or not verdict.key_facts:
        return 0.0
    stated = sum(fact.stated for fact in verdict.key_facts)
    return 1.0 if stated == len(verdict.key_facts) else 0.5 if stated else 0.0


def judge_correctness(judge: BaseChatModel, question: str, answer: str, reference: str) -> tuple[float, str]:
    """Answer correctness: does the answer state the key facts of the reference answer?"""
    prompt = CORRECTNESS_PROMPT.format(question=question, reference=reference, answer=answer)
    verdict = CorrectnessVerdict.model_validate(judge.with_structured_output(CorrectnessVerdict).invoke(prompt))
    return correctness_score(verdict), verdict.reason
