from fastapi import APIRouter, Depends, File, Form, HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_admin
from app.config import get_settings
from app.db import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.rag.document_processor import process_bytes
from app.rag.vector_store import delete_document, ingest_document
from app.schemas.document import DocumentListOut, DocumentOut, UploadResponse
from app.security.upload import UploadValidationError, validate_upload

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/documents", response_model=UploadResponse, dependencies=[Depends(require_admin)])
async def upload_document(
    file: UploadFile,
    department: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> UploadResponse:
    """Upload and ingest a document (admin only)."""
    settings = get_settings()

    try:
        content_bytes = await file.read()

        validate_upload(
            filename=file.filename,
            content_bytes=content_bytes,
            content_type=file.content_type or "application/octet-stream",
            max_size_mb=settings.max_upload_mb,
        )

        chunks = process_bytes(content_bytes, file.filename)

        doc = ingest_document(
            db,
            filename=file.filename,
            uploaded_by=user.id,
            department=department,
            chunks=chunks,
        )

        audit_entry = AuditLog(
            user_id=user.id,
            action="upload",
            question=f"Uploaded {file.filename} to {department}",
        )
        db.add(audit_entry)
        db.commit()

        return UploadResponse(
            document=DocumentOut.model_validate(doc),
            chunk_count=len(chunks),
        )

    except UploadValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}",
        )


@router.get("/documents", response_model=DocumentListOut, dependencies=[Depends(require_admin)])
def list_documents(
    department: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> DocumentListOut:
    """List documents (admin only, optionally filtered by department)."""
    from app.models.document import Document

    query = db.query(Document)

    if department:
        query = query.filter(Document.department == department)

    total = query.count()
    items = [
        DocumentOut.model_validate(doc)
        for doc in query.offset(skip).limit(limit).all()
    ]

    return DocumentListOut(items=items, total=total)


@router.delete("/documents/{document_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_doc(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> None:
    """Delete a document and its chunks (admin only)."""
    from uuid import UUID

    try:
        doc_id = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    try:
        from app.models.document import Document
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        delete_document(db, doc_id)

        audit_entry = AuditLog(
            user_id=user.id,
            action="delete",
            question=f"Deleted document {doc.filename}",
        )
        db.add(audit_entry)
        db.commit()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )
