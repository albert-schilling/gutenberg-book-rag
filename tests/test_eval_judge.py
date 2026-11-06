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


@pytest.mark.parametrize(
    ("verdict", "score"), [("correct", 1.0), ("partially_correct", 0.5), ("incorrect", 0.0)]
)
def test_correctness_verdicts_map_to_scores(verdict, score):
    fake = FakeJudge(judge.CorrectnessVerdict(verdict=verdict, reason="because"))
    assert judge.judge_correctness(fake, "Q?", "An answer.", "The reference.") == (score, "because")
    assert "The reference." in fake.prompts[0] and "An answer." in fake.prompts[0]
