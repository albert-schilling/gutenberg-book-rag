import numpy as np
import pytest

from book_rag.config import PASSAGE_PREFIX, QUERY_PREFIX
from book_rag.embeddings import build_embeddings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def embeddings():
    return build_embeddings()


def test_vectors_have_length_one(embeddings):
    """rag.retrieve converts the L2 distance into a cosine similarity, which needs length 1."""
    vectors = [embeddings.embed_query("What do penguins eat?"), *embeddings.embed_documents(["Penguins eat shrimp."])]
    assert [round(float(np.linalg.norm(v)), 4) for v in vectors] == [1.0, 1.0]


def test_queries_and_passages_get_their_prefixes(embeddings):
    model = embeddings._client
    text = "What do penguins eat?"
    assert np.allclose(embeddings.embed_query(text), model.encode(QUERY_PREFIX + text, normalize_embeddings=True), atol=1e-5)
    assert np.allclose(embeddings.embed_documents([text])[0], model.encode(PASSAGE_PREFIX + text, normalize_embeddings=True), atol=1e-5)
