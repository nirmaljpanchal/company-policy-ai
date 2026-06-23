from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chunk import DocChunk
from app.models.user import User


@dataclass
class RetrievedChunk:
    content: str
    source: str
    department: Optional[str]
    similarity_score: float


def get_allowed_departments(user: User) -> list[str]:
    """Map a User to their allowed departments for retrieval."""
    if user.role == "admin":
        return None
    return [user.department] if user.department else []


def retrieve(
    db: Session,
    query_embedding: list[float],
    allowed_departments: Optional[list[str]] = None,
    top_k: int = 5
) -> list[RetrievedChunk]:
    """Retrieve top-k chunks from pgvector with access control."""
    embedding_vector = Vector(query_embedding)

    query = select(
        DocChunk.content,
        DocChunk.source,
        DocChunk.department,
        (1 - func.cosine_distance(DocChunk.embedding, embedding_vector)).label("similarity")
    )

    if allowed_departments is not None:
        query = query.where(
            DocChunk.department.in_(allowed_departments)
        )

    query = query.order_by("similarity").limit(top_k)

    rows = db.execute(query).fetchall()

    return [
        RetrievedChunk(
            content=row.content,
            source=row.source,
            department=row.department,
            similarity_score=float(row.similarity)
        )
        for row in rows
    ]
