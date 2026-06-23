from typing import Optional
from uuid import UUID

from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.models.chunk import DocChunk
from app.models.document import Document as DocumentModel
from app.rag.embeddings import embed_texts


def ingest_document(
    db: Session,
    *,
    filename: str,
    uploaded_by: Optional[UUID],
    department: Optional[str],
    chunks: list[Document],
) -> DocumentModel:
    """
    Ingest a document with its chunks transactionally.

    Args:
        db: Database session
        filename: Name of the uploaded file
        uploaded_by: UUID of the user who uploaded
        department: Department identifier
        chunks: List of LangChain Document chunks

    Returns:
        Created Document model instance

    Raises:
        Exception: On any failure; status set to 'failed' and rolled back
    """
    try:
        doc = DocumentModel(
            filename=filename,
            uploaded_by=uploaded_by,
            department=department,
            status="processing",
        )
        db.add(doc)
        db.flush()

        chunk_texts = [chunk.page_content for chunk in chunks]
        embeddings = embed_texts(chunk_texts)

        for chunk, embedding in zip(chunks, embeddings):
            doc_chunk = DocChunk(
                document_id=doc.id,
                content=chunk.page_content,
                source=filename,
                department=department,
                embedding=embedding,
            )
            db.add(doc_chunk)

        doc.status = "ready"
        db.commit()
        return doc

    except Exception:
        if doc and hasattr(doc, "id") and doc.id:
            db.query(DocumentModel).filter(DocumentModel.id == doc.id).update(
                {DocumentModel.status: "failed"}
            )
        db.rollback()
        raise


def delete_document(db: Session, document_id: UUID) -> None:
    """
    Delete a document and its chunks (cascade handled by FK).

    Args:
        db: Database session
        document_id: UUID of the document to delete

    Raises:
        ValueError: If document not found
    """
    doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    db.delete(doc)
    db.commit()
