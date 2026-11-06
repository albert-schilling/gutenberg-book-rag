import pytest

from book_rag.evaluation import judge


class FakeJudge:
    """Mimics `chat_model.with_structured_output(Schema).invoke(prompt)` with a fixed verdict."""

    def __init__(self, verdict):
        self.verdict = verdict
        self.prompts = []

    def with_structured_output(self, schema):
        assert isinstance(self.verdict, schema)
        return self

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.verdict


def claims(*supported):
    return [judge.Claim(claim=f"claim {i}", supported=s) for i, s in enumerate(supported)]


def test_faithfulness_is_the_share_of_supported_claims():
    assert judge.faithfulness_score(claims(True, True, False, True)) == 0.75
    assert judge.faithfulness_score(claims(True)) == 1.0
    assert judge.faithfulness_score(claims(False)) == 0.0


def test_faithfulness_is_undefined_without_claims():
    assert judge.faithfulness_score([]) is None


def test_judge_faithfulness_returns_score_and_claims_and_shows_the_context():
    fake = FakeJudge(judge.FaithfulnessVerdict(claims=claims(True, False)))
    score, found = judge.judge_faithfulness(fake, "Why?", "Because.", "[Passage 1]\nthe context")
    assert score == 0.5
    assert [c.supported for c in found] == [True, False]
    assert "the context" in fake.prompts[0] and "Because." in fake.prompts[0] and "Why?" in fake.prompts[0]


def verdict(*stated, says_the_opposite=False):
    return judge.CorrectnessVerdict(
        key_facts=[judge.KeyFact(fact=f"fact {i}", stated=s) for i, s in enumerate(stated)],
        says_the_opposite=says_the_opposite,
        reason="because",
    )


@pytest.mark.parametrize(
    ("verdict_", "score"),
    [
        (verdict(True), 1.0),
        (verdict(True, True, True), 1.0),
        (verdict(True, False), 0.5),  # one of two key facts: partly right
        (verdict(False, False), 0.0),
        (verdict(True, True, says_the_opposite=True), 0.0),  # a wrong number or person: wrong, whatever else is right
        (verdict(), 0.0),  # no key facts found in the reference: nothing to give credit for
    ],
)
def test_the_score_follows_from_the_key_facts_that_the_answer_states(verdict_, score):
    assert judge.correctness_score(verdict_) == score


def test_judge_correctness_returns_the_score_and_the_reason_and_shows_both_texts():
    fake = FakeJudge(verdict(True, False))
    assert judge.judge_correctness(fake, "Q?", "An answer.", "The reference.") == (0.5, "because")
    assert "The reference." in fake.prompts[0] and "An answer." in fake.prompts[0]


def test_the_prompt_never_asks_the_judge_to_take_points_off_for_extra_detail():
    assert "Do NOT take points off for extra details" in judge.CORRECTNESS_PROMPT
