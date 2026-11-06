"""Retrieval quality with the real embedding model (cached locally), no language model involved.

The thresholds are a regression floor set just below the latest baseline report: they stop the
retrieval from getting worse. They are not a target. Raise them when the retrieval improves.
"""

import pytest

from book_rag import store
from book_rag.evaluation import metrics
from book_rag.evaluation.dataset import load_dataset
from book_rag.rag import retrieve

pytestmark = pytest.mark.integration

ANSWERABLE = [case for case in load_dataset() if case.answerable]

# Questions whose evidence the retriever does not find yet (see evals/reports). They are expected
# to fail; when one starts to pass it shows up as XPASS and can be removed from this set.
KNOWN_MISSES = {"nest-theft", "fasting", "food", "rookery-size", "enemies"}

MIN_CONTEXT_RECALL = 0.65
MIN_HIT_RATE = 0.65
MIN_MRR = 0.50


@pytest.fixture(scope="module")
def vector_store(tmp_path_factory):
    """The real vector store of the book, built once in a temporary directory."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(store, "CHROMA_DIR", tmp_path_factory.mktemp("chroma"))
        yield store.build_vector_store()


def retrieved_texts(case, vector_store):
    return [passage.page_content for passage, _ in retrieve(case.question, vector_store)]


def param(case):
    marks = [pytest.mark.xfail(reason="known retrieval miss", strict=False)] if case.id in KNOWN_MISSES else []
    return pytest.param(case, id=case.id, marks=marks)


@pytest.mark.parametrize("case", [param(c) for c in ANSWERABLE])
def test_the_evidence_is_retrieved(case, vector_store):
    assert metrics.hit(case.evidence, retrieved_texts(case, vector_store))


def test_retrieval_quality_does_not_regress(vector_store):
    texts = {case.id: retrieved_texts(case, vector_store) for case in ANSWERABLE}
    recall = metrics.mean([metrics.context_recall(c.evidence, texts[c.id]) for c in ANSWERABLE])
    hit_rate = metrics.mean([float(metrics.hit(c.evidence, texts[c.id])) for c in ANSWERABLE])
    mrr = metrics.mean([metrics.reciprocal_rank(c.evidence, texts[c.id]) for c in ANSWERABLE])
    assert recall >= MIN_CONTEXT_RECALL, f"context recall {recall:.2f}"
    assert hit_rate >= MIN_HIT_RATE, f"hit rate {hit_rate:.2f}"
    assert mrr >= MIN_MRR, f"MRR {mrr:.2f}"
