from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_auth_provider
from app.auth.deps import get_current_user
from app.db import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenPair:
    # NOTE: login/refresh are demo-only and disabled when AUTH_PROVIDER=azure_entra
    provider = get_auth_provider()

    user = provider.authenticate(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Write login audit log
    audit_entry = AuditLog(user_id=user.id, action="login")
    db.add(audit_entry)
    db.commit()

    return provider.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenPair:
    # NOTE: login/refresh are demo-only and disabled when AUTH_PROVIDER=azure_entra
    provider = get_auth_provider()

    try:
        return provider.refresh(db, request.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> UserOut:
    return user
