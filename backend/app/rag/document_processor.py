import os
import tempfile
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(file_path: str) -> list[Document]:
    """Load a document from disk using appropriate loader."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        loader = PyMuPDFLoader(file_path)
    elif ext in (".docx", ".doc"):
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader.load()


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    """Split documents into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(docs)


def process_file(file_path: str) -> list[Document]:
    """Load and chunk a file from disk."""
    docs = load_document(file_path)
    return chunk_documents(docs)


def process_bytes(
    content_bytes: bytes,
    filename: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    """
    Load and chunk a file from raw bytes.

    Writes bytes to a temp file with the correct extension, processes,
    and cleans up the temp file.
    """
    ext = Path(filename).suffix.lower()
    if ext not in {".pdf", ".docx", ".doc"}:
        raise ValueError(f"Unsupported file type: {ext}")

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=ext,
            delete=False,
        ) as tmp:
            tmp.write(content_bytes)
            temp_file = tmp.name

        docs = load_document(temp_file)
        return chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
