import pytest
from langchain_core.documents import Document

from book_rag import agent
from book_rag.agent import AgentResult, Step, agent_ask, merge
from book_rag.config import NO_ANSWER


class FakeVectorStore:
    """The passages depend on the query: `results` maps a query to [(start_index, distance)]."""

    def __init__(self, results):
        self.results = results
        self.queries = []

    def similarity_search_with_score(self, query, k):
        self.queries.append(query)
        return [(Document(page_content=f"passage {i}", metadata={"start_index": i}), d) for i, d in self.results.get(query, [])]


class ScriptedModel:
    """Returns the prepared steps one after the other and records the inputs of every call."""

    def __init__(self, *steps):
        self.steps, self.calls = list(steps), []

    def invoke(self, inputs):
        self.calls.append(inputs)
        return self.steps[len(self.calls) - 1]


STORE = {
    "Why do they do that?": [(1, 0.8), (2, 0.9)],
    "Why do skuas attack penguin chicks?": [(3, 0.2), (4, 0.3)],
    "skuas feed on chicks": [(4, 0.1), (5, 0.4)],
}


def test_a_question_that_the_first_passages_answer_costs_one_call_and_one_search():
    model, store = ScriptedModel(Step(answer="Because they are hungry.")), FakeVectorStore(STORE)
    result = agent_ask("Why do they do that?", store, model)
    assert result == AgentResult("Because they are hungry.", result.passages, ["Why do they do that?"])
    assert len(model.calls) == 1 and store.queries == ["Why do they do that?"]


def test_the_model_can_search_again_with_a_new_query_and_then_answers():
    model = ScriptedModel(Step(new_queries=["Why do skuas attack penguin chicks?"]), Step(answer="They eat them."))
    store = FakeVectorStore(STORE)
    result = agent_ask("Why do they do that?", store, model, conversation="Q: What do skuas do?\nA: They kill chicks.")

    assert result.answer == "They eat them."
    assert result.queries == ["Why do they do that?", "Why do skuas attack penguin chicks?"]
    assert store.queries == result.queries  # the only tool is a search in this book
    assert [p.metadata["start_index"] for p, _ in result.passages] == [3, 4, 1, 2]  # both searches, best first
    first, second = model.calls
    assert "passage 1" in first["context"] and "passage 3" not in first["context"]
    assert "passage 3" in second["context"]  # the model sees the passages of the new search
    assert first["conversation"].startswith("Q: What do skuas do?")  # and the conversation, to rewrite the query
    assert "“Why do they do that?”" in first["searched"] and "“Why do skuas attack" in second["searched"]
    assert "2 more time" in first["rule"] and "1 more time" in second["rule"]


def test_the_search_stops_after_the_last_round_and_the_model_must_give_a_final_answer():
    steps = [Step(new_queries=["q1"]), Step(new_queries=["q2"]), Step(answer=NO_ANSWER)]
    model, store = ScriptedModel(*steps), FakeVectorStore({})
    result = agent_ask("What?", store, model)
    assert len(model.calls) == agent.MAX_ROUNDS == 3  # never more calls than rounds
    assert store.queries == ["What?", "q1", "q2"]
    assert "cannot search again" in model.calls[-1]["rule"] and NO_ANSWER in model.calls[-1]["rule"]
    assert result.answer == NO_ANSWER


def test_a_model_that_still_asks_for_a_search_in_the_last_round_gets_the_refusal():
    model = ScriptedModel(Step(new_queries=["a"]), Step(new_queries=["b"]), Step(new_queries=["c"]))
    result = agent_ask("What?", FakeVectorStore({"What?": [(1, 0.5)]}), model)
    assert result.answer == NO_ANSWER and len(model.calls) == 3
    assert result.queries == ["What?", "a", "b"]  # "c" was never searched


def test_repeated_blank_and_too_many_queries_are_dropped():
    model = ScriptedModel(
        Step(new_queries=["What?", "  ", "new one", "another", "a third"]), Step(answer="Done.")
    )
    store = FakeVectorStore({})
    result = agent_ask("What?", store, model)
    assert result.queries == ["What?", "new one", "another"]  # not the same query again, not blank, at most two


def test_no_answer_and_no_new_query_means_the_refusal_without_more_calls():
    model = ScriptedModel(Step())
    result = agent_ask("What?", FakeVectorStore({"What?": [(1, 0.5)]}), model)
    assert result.answer == NO_ANSWER and len(model.calls) == 1


def test_a_blank_answer_counts_as_no_answer():
    model = ScriptedModel(Step(answer="   ", new_queries=["other words"]), Step(answer="Found."))
    assert agent_ask("What?", FakeVectorStore({}), model).answer == "Found."


def test_merge_keeps_each_passage_once_with_its_best_score_and_the_best_few():
    doc = lambda i: Document(page_content=str(i), metadata={"start_index": i})  # noqa: E731
    first = [(doc(1), 0.5), (doc(2), 0.9)]
    second = [(doc(1), 0.7), (doc(3), 0.1), (doc(4), 0.6), (doc(5), 0.55), (doc(6), 0.2), (doc(7), 0.05)]
    merged = [(p.metadata["start_index"], s) for p, s in merge(first, second)]
    assert merged == [(2, 0.9), (1, 0.7), (4, 0.6), (5, 0.55), (6, 0.2), (3, 0.1)]  # passage 1 once, with 0.7; 7 is cut
    assert len(merged) == agent.MAX_PASSAGES


def test_the_offline_step_chain_answers_without_a_model(monkeypatch):
    monkeypatch.setattr(agent, "OFFLINE", True)
    from book_rag.books import DEFAULT_BOOK

    step = agent.build_step_chain(DEFAULT_BOOK).invoke({"question": "Why?"})
    assert isinstance(step, Step) and "Offline mode" in step.answer and "Why?" in step.answer


def test_the_agent_prompt_allows_only_rephrasing_and_searching_this_book():
    assert "search this book again" in agent.AGENT_RULE
    assert "web" not in (agent.AGENT_RULE + agent.AGENT_INSTRUCTIONS).lower()  # no web search, and no other tool


def test_the_agent_prompt_does_not_tell_the_model_to_refuse_before_it_has_searched():
    from book_rag import rag
    from book_rag.books import DEFAULT_BOOK
    from book_rag.config import NO_ANSWER

    plain = rag.build_system_prompt(DEFAULT_BOOK)
    agentic = rag.build_system_prompt(DEFAULT_BOOK, refusal_rule=agent.AGENT_RULE)
    assert NO_ANSWER in plain  # the plain pipeline refuses at once
    assert NO_ANSWER not in agentic  # the agent only refuses in its last round (MUST_ANSWER)
    assert "{max_queries}" in agentic and "{context}" in agentic
