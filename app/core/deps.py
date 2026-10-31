"""FastAPI dependencies for auth and DB."""

from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import decode_access_token
from app.models.user import User, UserRole

bearer = HTTPBearer(auto_error=False)


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> User | None:
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        return None
    return db.get(User, user_id)


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None or user.account_status != "active":
        raise APIError(401, "UNAUTHORIZED", "Authentication required.")
    return user


def require_roles(*roles: str):
    def _checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        owned = {r.role for r in db.query(UserRole).filter(UserRole.user_id == user.id).all()}
        if "admin" in owned:
            return user
        if not owned.intersection(set(roles)):
            raise APIError(403, "FORBIDDEN", "You do not have permission for this action.")
        return user

    return _checker


def idempotency_key(x_idempotency_key: str | None = Header(default=None)) -> str | None:
    return x_idempotency_key
