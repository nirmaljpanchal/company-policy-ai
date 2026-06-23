import io
from uuid import uuid4
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models.document import Document
from app.models.chunk import DocChunk
from app.models.user import User


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for tests."""
    user = User(
        id=uuid4(),
        email="admin@test.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def employee_user(db: Session) -> User:
    """Create an employee user for tests."""
    user = User(
        id=uuid4(),
        email="employee@test.com",
        password_hash=hash_password("password123"),
        role="employee",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create an access token for the admin user."""
    return create_access_token(subject=str(admin_user.id), role="admin")


@pytest.fixture
def employee_token(employee_user: User) -> str:
    """Create an access token for the employee user."""
    return create_access_token(subject=str(employee_user.id), role="employee")


@pytest.fixture
def small_pdf() -> bytes:
    """Create a minimal valid PDF for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>
endobj
4 0 obj
<< >>
stream
BT
/F1 12 Tf
50 750 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
265
%%EOF
"""
    return pdf_content


@pytest.fixture
def small_docx() -> bytes:
    """Create a minimal valid DOCX (ZIP) for testing."""
    # Minimal ZIP header that will pass magic byte check
    zip_content = b"PK\x03\x04" + b"\x00" * 100
    return zip_content


def test_admin_upload_pdf_success(
    client: TestClient,
    admin_token: str,
    small_pdf: bytes,
    db: Session,
) -> None:
    """Test successful PDF upload by admin."""
    with patch("app.rag.embeddings.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 1536 for _ in range(2)]

        response = client.post(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.pdf", io.BytesIO(small_pdf), "application/pdf")},
            data={"department": "HR"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "document" in data
    assert data["document"]["filename"] == "test.pdf"
    assert data["document"]["status"] == "ready"
    assert data["document"]["department"] == "HR"
    assert data["chunk_count"] == 2

    doc = db.query(Document).filter(Document.filename == "test.pdf").first()
    assert doc is not None
    assert doc.status == "ready"

    chunks = db.query(DocChunk).filter(DocChunk.document_id == doc.id).all()
    assert len(chunks) == 2


def test_employee_upload_denied(
    client: TestClient,
    employee_token: str,
    small_pdf: bytes,
) -> None:
    """Test that employee cannot upload documents."""
    response = client.post(
        "/admin/documents",
        headers={"Authorization": f"Bearer {employee_token}"},
        files={"file": ("test.pdf", io.BytesIO(small_pdf), "application/pdf")},
        data={"department": "HR"},
    )

    assert response.status_code == 403


def test_upload_oversized_file(
    client: TestClient,
    admin_token: str,
    db: Session,
) -> None:
    """Test rejection of oversized files."""
    oversized_content = b"%PDF" + b"\x00" * (11 * 1024 * 1024)

    response = client.post(
        "/admin/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("large.pdf", io.BytesIO(oversized_content), "application/pdf")},
        data={"department": "HR"},
    )

    assert response.status_code == 422


def test_upload_wrong_extension(
    client: TestClient,
    admin_token: str,
) -> None:
    """Test rejection of unsupported file extensions."""
    response = client.post(
        "/admin/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")},
        data={"department": "HR"},
    )

    assert response.status_code == 422


def test_upload_mime_mismatch(
    client: TestClient,
    admin_token: str,
) -> None:
    """Test rejection when MIME type doesn't match extension."""
    response = client.post(
        "/admin/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("test.pdf", io.BytesIO(b"not a pdf"), "text/plain")},
        data={"department": "HR"},
    )

    assert response.status_code == 422


def test_list_documents_empty(
    client: TestClient,
    admin_token: str,
) -> None:
    """Test listing documents when none exist."""
    response = client.get(
        "/admin/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_documents_with_filter(
    client: TestClient,
    admin_token: str,
    small_pdf: bytes,
    db: Session,
) -> None:
    """Test listing documents with department filter."""
    with patch("app.rag.embeddings.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 1536]

        client.post(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test1.pdf", io.BytesIO(small_pdf), "application/pdf")},
            data={"department": "HR"},
        )

        client.post(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test2.pdf", io.BytesIO(small_pdf), "application/pdf")},
            data={"department": "Finance"},
        )

    response = client.get(
        "/admin/documents?department=HR",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["department"] == "HR"


def test_delete_document_success(
    client: TestClient,
    admin_token: str,
    small_pdf: bytes,
    db: Session,
) -> None:
    """Test successful document deletion with cascade delete of chunks."""
    with patch("app.rag.embeddings.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 1536 for _ in range(2)]

        response = client.post(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.pdf", io.BytesIO(small_pdf), "application/pdf")},
            data={"department": "HR"},
        )

    doc_id = response.json()["document"]["id"]

    doc = db.query(Document).filter(Document.id == doc_id).first()
    assert doc is not None
    chunks_before = db.query(DocChunk).filter(DocChunk.document_id == doc_id).count()
    assert chunks_before > 0

    response = client.delete(
        f"/admin/documents/{doc_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204

    doc_after = db.query(Document).filter(Document.id == doc_id).first()
    assert doc_after is None

    chunks_after = db.query(DocChunk).filter(DocChunk.document_id == doc_id).count()
    assert chunks_after == 0


def test_delete_nonexistent_document(
    client: TestClient,
    admin_token: str,
) -> None:
    """Test deletion of a non-existent document."""
    fake_id = str(uuid4())

    response = client.delete(
        f"/admin/documents/{fake_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


def test_delete_invalid_document_id(
    client: TestClient,
    admin_token: str,
) -> None:
    """Test deletion with invalid document ID format."""
    response = client.delete(
        "/admin/documents/not-a-uuid",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400


def test_upload_audit_log(
    client: TestClient,
    admin_user: User,
    admin_token: str,
    small_pdf: bytes,
    db: Session,
) -> None:
    """Test that upload is logged in audit_log."""
    from app.models.audit import AuditLog

    with patch("app.rag.embeddings.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 1536]

        client.post(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.pdf", io.BytesIO(small_pdf), "application/pdf")},
            data={"department": "HR"},
        )

    audit_entries = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == admin_user.id)
        .filter(AuditLog.action == "upload")
        .all()
    )

    assert len(audit_entries) > 0
    assert "test.pdf" in audit_entries[0].question


def test_delete_audit_log(
    client: TestClient,
    admin_user: User,
    admin_token: str,
    small_pdf: bytes,
    db: Session,
) -> None:
    """Test that deletion is logged in audit_log."""
    from app.models.audit import AuditLog

    with patch("app.rag.embeddings.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1] * 1536]

        response = client.post(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.pdf", io.BytesIO(small_pdf), "application/pdf")},
            data={"department": "HR"},
        )

    doc_id = response.json()["document"]["id"]

    client.delete(
        f"/admin/documents/{doc_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    audit_entries = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == admin_user.id)
        .filter(AuditLog.action == "delete")
        .all()
    )

    assert len(audit_entries) > 0
    assert "test.pdf" in audit_entries[0].question
