import re

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from book_rag import store
from book_rag.books import BOOKS, DEFAULT_BOOK


def stored(vector_store):
    """How many chunks are in a vector store (public API only)."""
    return len(vector_store.get()["ids"])


def patch_store(monkeypatch, tmp_path):
    """Use fake embeddings and a temporary directory: no model download, no real chroma_db."""
    monkeypatch.setattr(store, "build_embeddings", lambda: DeterministicFakeEmbedding(size=16))
    monkeypatch.setattr(store, "CHROMA_DIR", tmp_path / "chroma_db")


def test_the_book_is_embedded_once(monkeypatch, tmp_path):
    patch_store(monkeypatch, tmp_path)

    first = store.build_vector_store(DEFAULT_BOOK)
    count = stored(first)
    assert count > 200

    added = []
    monkeypatch.setattr(type(first), "add_documents", lambda self, *args, **kwargs: added.append(1))
    second = store.build_vector_store(DEFAULT_BOOK)  # the store is not empty: nothing is added again
    assert stored(second) == count
    assert added == []


def test_chunks_have_content_hash_ids_start_index_and_the_book(monkeypatch, tmp_path):
    patch_store(monkeypatch, tmp_path)
    vector_store = store.build_vector_store(DEFAULT_BOOK)

    stored = vector_store.get(include=["metadatas"])
    assert len(set(stored["ids"])) == len(stored["ids"])  # unique
    assert all(len(id_) == 40 for id_ in stored["ids"])  # SHA-1 hex digest
    assert all("start_index" in metadata for metadata in stored["metadatas"])
    assert {metadata["book"] for metadata in stored["metadatas"]} == {DEFAULT_BOOK.id}


def test_every_book_gets_its_own_collection_in_the_same_folder(monkeypatch, tmp_path):
    patch_store(monkeypatch, tmp_path)
    penguins = store.build_vector_store(BOOKS["antarctic_penguins_levick"])
    oz = store.build_vector_store(BOOKS["wonderful_wizard_of_oz_baum"])

    assert penguins._collection.name.startswith("antarctic_penguins_levick-")
    assert oz._collection.name.startswith("wonderful_wizard_of_oz_baum-")
    assert penguins._collection.id != oz._collection.id
    assert {m["book"] for m in oz.get(include=["metadatas"])["metadatas"]} == {"wonderful_wizard_of_oz_baum"}
    # a search in one book never returns text of the other
    answers = " ".join(d.page_content for d in oz.similarity_search("penguins and skuas", k=10))
    assert "skua" not in answers.lower()


def test_a_changed_setting_builds_a_new_collection(monkeypatch, tmp_path):
    """The collection name contains a fingerprint of the settings, so stale vectors are never reused."""
    patch_store(monkeypatch, tmp_path)
    first = store.build_vector_store(DEFAULT_BOOK)

    monkeypatch.setattr(store, "CHUNK_SIZE", 500)
    second = store.build_vector_store(DEFAULT_BOOK)

    assert second._collection.name != first._collection.name
    assert stored(second) > stored(first) > 0  # built from scratch with smaller chunks


def test_a_changed_text_builds_a_new_collection():
    assert store.collection_name(DEFAULT_BOOK, "text one") != store.collection_name(DEFAULT_BOOK, "text two")
    assert store.collection_name(DEFAULT_BOOK, "text one") == store.collection_name(DEFAULT_BOOK, "text one")


@pytest.mark.parametrize("book", BOOKS.values(), ids=lambda b: b.id)
def test_collection_names_are_valid_for_chroma(book):
    name = store.collection_name(book, "some text")
    assert re.fullmatch(rf"{book.id}-[0-9a-f]{{8}}", name)
    assert 3 <= len(name) <= 63  # Chroma's limit
