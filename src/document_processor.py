import os
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(file_path: str) -> list:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        loader = PyMuPDFLoader(file_path)
    elif ext in (".docx", ".doc"):
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader.load()


def chunk_documents(docs: list, chunk_size: int = 500, chunk_overlap: int = 50) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(docs)


def process_file(file_path: str) -> list:
    docs = load_document(file_path)
    return chunk_documents(docs)
