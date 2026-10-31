"""Auth and account endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AgentOnboardRequest,
    LoginRequest,
    PreferencesUpdate,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import MessageOut
from app.services import auth_service

router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return auth_service.register_user(db, payload)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_user(db, payload.email, payload.password)


@router.post("/auth/logout", response_model=MessageOut)
def logout(user: User = Depends(get_current_user)):
    # JWT is stateless in MVP; client discards token. Refresh revocation can be added with Redis.
    return MessageOut(message="Logged out. Discard the access token client-side.", details={"user_id": str(user.id)})


@router.get("/accounts/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.user_out(db, user)


@router.patch("/accounts/me/preferences", response_model=UserOut)
def preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return auth_service.update_preferences(db, user, payload)


@router.post("/accounts/me/agent-onboarding", response_model=UserOut)
def agent_onboarding(
    payload: AgentOnboardRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return auth_service.onboard_agent(db, user, payload)
