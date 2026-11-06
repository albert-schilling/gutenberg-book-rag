from langchain_core.embeddings import DeterministicFakeEmbedding

from book_rag import store


def patch_store(monkeypatch, tmp_path):
    """Use fake embeddings and a temporary directory: no model download, no real chroma_db."""
    monkeypatch.setattr(store, "HuggingFaceEmbeddings", lambda model_name: DeterministicFakeEmbedding(size=16))
    monkeypatch.setattr(store, "CHROMA_DIR", tmp_path / "chroma_db")


def test_the_book_is_embedded_once(monkeypatch, tmp_path):
    patch_store(monkeypatch, tmp_path)

    first = store.build_vector_store()
    count = first._collection.count()
    assert count > 200

    added = []
    monkeypatch.setattr(type(first), "add_documents", lambda self, *args, **kwargs: added.append(1))
    second = store.build_vector_store()  # the store is not empty: nothing is added again
    assert second._collection.count() == count
    assert added == []


def test_chunks_have_content_hash_ids_and_start_index(monkeypatch, tmp_path):
    patch_store(monkeypatch, tmp_path)
    vector_store = store.build_vector_store()

    stored = vector_store.get(include=["metadatas"])
    assert len(set(stored["ids"])) == len(stored["ids"])  # unique
    assert all(len(id_) == 40 for id_ in stored["ids"])  # SHA-1 hex digest
    assert all("start_index" in metadata for metadata in stored["metadatas"])
