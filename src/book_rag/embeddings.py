"""The embedding model."""

from langchain_huggingface import HuggingFaceEmbeddings

from book_rag.config import EMBEDDING_MODEL, PASSAGE_PREFIX, QUERY_PREFIX


def build_embeddings() -> HuggingFaceEmbeddings:
    """Embeddings of length 1, with the prefixes of the e5 model.

    Length 1 matters: `rag.retrieve` turns Chroma's squared L2 distance into a cosine
    similarity with `1 - distance / 2`, which is only exact for vectors of length 1.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True, "prompt": PASSAGE_PREFIX},
        query_encode_kwargs={"normalize_embeddings": True, "prompt": QUERY_PREFIX},
    )
