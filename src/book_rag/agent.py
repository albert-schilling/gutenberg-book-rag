"""An agentic answer: the model may search the book again with new questions before it answers.

The only tool is a search in the vector store of this one book. There is no web search and no other tool: the
model can only rephrase the question or ask new ones, and the answer is still based on passages of the book.

Every extra round is another call, and the free Groq plan allows 8,000 tokens a minute, so the loop is short:
a question that the first passages answer costs exactly one call, as without the agent.
"""

import logging
from dataclasses import dataclass, field

from langchain_chroma import Chroma
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from book_rag.books import Book
from book_rag.config import FALLBACK_ANSWER, LLM_MODEL, NO_ANSWER, OFFLINE, TOP_K
from book_rag.rag import ScoredPassages, _offline_reply, build_system_prompt, format_context, retrieve

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3  # searches in the book per question: the first one and at most two more
NEW_QUERIES_PER_ROUND = 2
MAX_PASSAGES = TOP_K + 2  # passages kept when the results of several searches are put together

AGENT_RULE = (
    "You can search this book again, and you answer by filling in the fields: if the passages (or the summary) answer "
    "the question, put the answer in `answer`. If they do not, do not answer and do not refuse yet: put up to "
    "{max_queries} new search queries in `new_queries`. Each query must stand on its own (resolve words like "
    '"they" with the conversation) and use other words than the searches before: synonyms, or how the book itself would say it.'
)
AGENT_INSTRUCTIONS = """

{rule}

Already searched for: {searched}"""
CAN_SEARCH = "You may still search {left} more time(s)."
MUST_ANSWER = f'You cannot search again. If the passages do not answer the question, set `answer` to exactly "{NO_ANSWER}".'


class Step(BaseModel):
    """What the model decides after it has read the passages."""

    answer: str | None = Field(default=None, description="The final answer, if the passages are enough; else null")
    new_queries: list[str] = Field(default_factory=list, description="New search queries, if they are not enough")


@dataclass
class AgentResult:
    answer: str
    passages: ScoredPassages
    queries: list[str] = field(default_factory=list)  # every search in the book, the first one is the question
    error: bool = False  # the language model could not answer: `answer` is a message for the reader


def build_step_chain(book: Book) -> Runnable:
    """The model that answers or asks for another search. Returns a `Step`."""
    if OFFLINE:
        return RunnableLambda(lambda inputs: Step(answer=_offline_reply(inputs)))
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", build_system_prompt(book, refusal_rule=AGENT_RULE) + AGENT_INSTRUCTIONS),
            ("human", "{question}"),
        ]
    )
    llm: BaseChatModel = ChatGroq(model=LLM_MODEL, temperature=0, max_retries=2)
    return prompt | llm.with_structured_output(Step)


def merge(passages: ScoredPassages, new: ScoredPassages) -> ScoredPassages:
    """Put the passages of two searches together: no passage twice, the most similar ones first, at most MAX_PASSAGES."""
    best: dict[int, tuple] = {}
    for passage, score in [*passages, *new]:
        key = passage.metadata["start_index"]
        if key not in best or score > best[key][1]:
            best[key] = (passage, score)
    return sorted(best.values(), key=lambda pair: pair[1], reverse=True)[:MAX_PASSAGES]


def agent_ask(
    question: str, vector_store: Chroma, step_chain: Runnable, conversation: str = ""
) -> AgentResult:
    """Answer a question, searching the book again with new queries when the passages are not enough."""
    queries = [question]
    passages = retrieve(question, vector_store)
    for round_number in range(1, MAX_ROUNDS + 1):
        last_round = round_number == MAX_ROUNDS
        step = step_chain.invoke(
            {
                "context": format_context(passages),
                "question": question,
                "conversation": conversation or "(none)",
                "searched": "; ".join(f"“{q}”" for q in queries),
                "max_queries": NEW_QUERIES_PER_ROUND,
                "rule": MUST_ANSWER if last_round else CAN_SEARCH.format(left=MAX_ROUNDS - round_number),
            }
        )
        if step.answer and step.answer.strip():
            return AgentResult(step.answer.strip(), passages, queries)
        fresh = [q.strip() for q in step.new_queries if q.strip() and q.strip() not in queries][:NEW_QUERIES_PER_ROUND]
        if last_round or not fresh:
            break
        for query in fresh:
            queries.append(query)
            passages = merge(passages, retrieve(query, vector_store))
    return AgentResult(NO_ANSWER if passages else FALLBACK_ANSWER, passages, queries)
