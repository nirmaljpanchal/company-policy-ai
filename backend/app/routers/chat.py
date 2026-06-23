from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.rag.graph import RAGState, RAGGraph
from app.rag.retriever import get_allowed_departments
from app.schemas.chat import ChatRequest, ChatResponse
from app.security.moderation import check_output
from app.services.quota import check_and_increment

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    http_request: Request = None
) -> ChatResponse:
    """POST /chat endpoint with quota, guards, RAG, and audit."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    quota_result = check_and_increment(db, user.id)
    if not quota_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily query limit exceeded",
            headers={"X-Quota-Remaining": "0"}
        )

    allowed_departments = get_allowed_departments(user)

    state = RAGState(
        question=request.question,
        chat_history=request.chat_history or [],
        user=user,
        allowed_departments=allowed_departments
    )

    graph = RAGGraph(db)
    final_state = graph.invoke(state)

    if final_state.blocked:
        safe_answer = (
            "I cannot process that request due to a security concern. "
            "Please rephrase your question or contact your administrator."
        )
        audit_log = AuditLog(
            user_id=user.id,
            action="query",
            question=request.question,
            sources=None,
            ip=http_request.client.host if http_request else None
        )
        db.add(audit_log)
        db.commit()

        return ChatResponse(
            answer=safe_answer,
            sources=[],
            quota_remaining=quota_result.remaining,
            blocked=True,
            block_reason=final_state.block_reason
        )

    answer = final_state.answer
    mod_result = check_output(answer)
    if mod_result.flagged:
        safe_answer = (
            "I cannot provide that response due to content policy. "
            "Please contact your administrator if you believe this is an error."
        )
        answer = safe_answer

    sources_data = [
        {
            "source": src,
            "similarity": next(
                (doc["similarity_score"] for doc in final_state.retrieved_docs if doc["source"] == src),
                0.0
            )
        }
        for src in final_state.sources
    ]

    audit_log = AuditLog(
        user_id=user.id,
        action="query",
        question=request.question,
        sources=sources_data,
        ip=http_request.client.host if http_request else None
    )
    db.add(audit_log)
    db.commit()

    return ChatResponse(
        answer=answer,
        sources=final_state.sources,
        quota_remaining=quota_result.remaining,
        blocked=False
    )
