"""The Chroma vector store with the chunks of the book."""

import hashlib
import logging

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from book_rag.book import load_book
from book_rag.config import CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAME, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def build_vector_store() -> Chroma:
    """Open the Chroma vector store and fill it with the book, but only if it is empty."""
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    # Embed the book only on the first run, not on every start
    if vector_store._collection.count() == 0:
        logger.info("Building the vector store (first run only) ...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, add_start_index=True
        )
        chunks = splitter.split_documents([load_book()])
        ids = [hashlib.sha1(chunk.page_content.encode("utf-8")).hexdigest() for chunk in chunks]
        vector_store.add_documents(chunks, ids=ids)

    return vector_store
