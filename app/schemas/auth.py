"""Auth and account schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    phone: str | None = None
    role: str = "consumer"
    consent_purpose: str = "account_creation"
    policy_version: str = "1.0"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    roles: list[str]


class AgentOnboardRequest(BaseModel):
    agency_name: str
    contact_phone: str | None = None
    registration_reference: str | None = None


class PreferencesUpdate(BaseModel):
    budget_min: float | None = None
    budget_max: float | None = None
    preferred_locations: list[str] = Field(default_factory=list)
    configuration: list[str] = Field(default_factory=list)
    purpose: str | None = None
    commute_destination: str | None = None
    max_commute_minutes: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class UserOut(ORMModel):
    id: UUID
    email: str | None
    phone: str | None
    full_name: str | None
    account_status: str
    preferences: dict[str, Any]
    roles: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
