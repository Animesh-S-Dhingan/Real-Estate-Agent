"""Authentication and account services."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import ConsentRecord, Organisation, OrganisationMembership, User, UserRole
from app.schemas.auth import AgentOnboardRequest, PreferencesUpdate, RegisterRequest, TokenResponse, UserOut


ALLOWED_ROLES = {
    "consumer",
    "property_owner",
    "agent",
    "developer",
    "admin",
    "verification_reviewer",
    "support_agent",
}


def _roles_for(db: Session, user: User) -> list[str]:
    return [r.role for r in db.query(UserRole).filter(UserRole.user_id == user.id).all()]


def user_out(db: Session, user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        account_status=user.account_status,
        preferences=user.preferences or {},
        roles=_roles_for(db, user),
        created_at=user.created_at,
    )


def register_user(db: Session, payload: RegisterRequest) -> TokenResponse:
    if payload.role not in ALLOWED_ROLES - {"admin"}:
        # admin cannot self-register
        if payload.role == "admin":
            raise APIError(403, "FORBIDDEN", "Admin accounts cannot be self-registered.")
        raise APIError(400, "VALIDATION_ERROR", "Invalid role.", {"role": [f"Must be one of {sorted(ALLOWED_ROLES - {'admin'})}"]})

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise APIError(400, "VALIDATION_ERROR", "Unable to register with provided credentials.")

    user = User(
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        preferences={},
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role=payload.role))
    db.add(
        ConsentRecord(
            user_id=user.id,
            purpose=payload.consent_purpose,
            consent_status="granted",
            policy_version=payload.policy_version,
        )
    )
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, {"roles": _roles_for(db, user)})
    return TokenResponse(access_token=token, user_id=user.id, roles=_roles_for(db, user))


def login_user(db: Session, email: str, password: str) -> TokenResponse:
    user = db.query(User).filter(User.email == email.lower()).first()
    # Generic error — do not reveal account existence
    if not user or not verify_password(password, user.password_hash):
        raise APIError(401, "UNAUTHORIZED", "Invalid credentials.")
    if user.account_status != "active":
        raise APIError(403, "FORBIDDEN", "Account is not active.")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    roles = _roles_for(db, user)
    token = create_access_token(user.id, {"roles": roles})
    return TokenResponse(access_token=token, user_id=user.id, roles=roles)


def update_preferences(db: Session, user: User, payload: PreferencesUpdate) -> UserOut:
    prefs = dict(user.preferences or {})
    prefs.update(payload.model_dump(exclude_none=True))
    user.preferences = prefs
    db.commit()
    db.refresh(user)
    return user_out(db, user)


def onboard_agent(db: Session, user: User, payload: AgentOnboardRequest) -> UserOut:
    org = Organisation(
        name=payload.agency_name,
        organisation_type="agency",
        verification_status="pending",
        registration_reference=payload.registration_reference,
        contact_email=user.email,
        contact_phone=payload.contact_phone,
    )
    db.add(org)
    db.flush()
    db.add(OrganisationMembership(organisation_id=org.id, user_id=user.id, role="agent", status="active"))
    roles = _roles_for(db, user)
    if "agent" not in roles:
        db.add(UserRole(user_id=user.id, role="agent", organisation_id=org.id))
    db.commit()
    db.refresh(user)
    return user_out(db, user)
