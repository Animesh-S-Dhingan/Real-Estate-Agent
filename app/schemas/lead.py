"""Lead CRM schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LeadCreate(BaseModel):
    listing_id: UUID
    message: str = Field(min_length=5)
    contact_preference: str = "phone"
    requester_name: str | None = None
    requester_email: str | None = None
    requester_phone: str | None = None
    idempotency_key: str | None = None


class LeadUpdate(BaseModel):
    status: str | None = None
    assigned_agent_id: UUID | None = None


class LeadActivityCreate(BaseModel):
    activity_type: str
    new_value: str | None = None


class LeadOut(ORMModel):
    id: UUID
    listing_id: UUID
    requester_user_id: UUID | None
    assigned_agent_id: UUID | None
    organisation_id: UUID | None
    message: str
    contact_preference: str
    requester_name: str | None
    requester_email: str | None
    requester_phone: str | None
    status: str
    created_at: datetime
    updated_at: datetime
