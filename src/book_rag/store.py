"""The Chroma vector store: one collection per book, all in the same folder."""

import hashlib
import logging

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from book_rag.book import load_book
from book_rag.books import Book
from book_rag.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    PASSAGE_PREFIX,
    QUERY_PREFIX,
)
from book_rag.embeddings import build_embeddings

logger = logging.getLogger(__name__)


def collection_name(book: Book, text: str) -> str:
    """The name of the book's collection, with a fingerprint of everything that decides what is stored.

    After a change of the embedding model, the chunking or the cleaned text of the book, the name changes,
    so a fresh collection is built instead of reusing stale vectors.
    """
    settings = f"{EMBEDDING_MODEL}|{QUERY_PREFIX}|{PASSAGE_PREFIX}|{CHUNK_SIZE}|{CHUNK_OVERLAP}|{text}"
    return f"{book.id}-{hashlib.sha1(settings.encode('utf-8')).hexdigest()[:8]}"


def build_vector_store(book: Book) -> Chroma:
    """Open the collection of the book and fill it with the chunks of the book, but only if it is empty."""
    document = load_book(book)
    vector_store = Chroma(
        collection_name=collection_name(book, document.page_content),
        embedding_function=build_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

    # Embed the book only on the first run, not on every start
    if not vector_store.get(limit=1)["ids"]:
        logger.info("Building the vector store of '%s' (first time only) ...", book.title)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, add_start_index=True
        )
        chunks = splitter.split_documents([document])
        ids = [hashlib.sha1(chunk.page_content.encode("utf-8")).hexdigest() for chunk in chunks]
        vector_store.add_documents(chunks, ids=ids)

    return vector_store
