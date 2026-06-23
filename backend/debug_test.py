#!/usr/bin/env python
import os
import io
import tempfile
from unittest.mock import patch
from uuid import uuid4

# Setup test env before imports
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
test_db_path = test_db_file.name
test_db_file.close()

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.db import Base, SessionLocal, get_db, engine
from app.main import app
from app.models.user import User

# Create tables
Base.metadata.create_all(bind=engine)
session = SessionLocal()

# Create admin user
admin = User(
    id=uuid4(),
    email="admin@test.com",
    password_hash=hash_password("password123"),
    role="admin",
    is_active=True,
)
session.add(admin)
session.commit()

# Setup client
client = TestClient(app)
admin_token = create_access_token(subject=str(admin.id), role="admin")

def override_get_db():
    yield session

app.dependency_overrides[get_db] = override_get_db

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

print("Testing upload...")
with patch("app.rag.embeddings.embed_texts") as mock_embed:
    mock_embed.return_value = [[0.1] * 1536 for _ in range(2)]
    try:
        response = client.post(
            "/admin/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"department": "HR"},
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:1000]}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

session.close()
os.remove(test_db_path)
