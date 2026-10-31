from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional, idempotency_key, require_roles
from app.models.user import User
from app.schemas.lead import LeadActivityCreate, LeadCreate, LeadOut, LeadUpdate
from app.services import leads as lead_service

router = APIRouter()


@router.post("/leads", response_model=LeadOut)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    key: str | None = Depends(idempotency_key),
):
    return lead_service.create_lead(db, payload, user, key)


@router.get("/agent/leads", response_model=list[LeadOut])
def agent_leads(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("agent", "admin", "property_owner")),
):
    return lead_service.list_agent_leads(db, user, status=status)


@router.patch("/agent/leads/{lead_id}", response_model=LeadOut)
def patch_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("agent", "admin")),
):
    return lead_service.update_lead(db, lead_id, payload, user)


@router.post("/leads/{lead_id}/activities")
def lead_activity(
    lead_id: UUID,
    payload: LeadActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    activity = lead_service.add_activity(db, lead_id, payload, user)
    return {
        "id": str(activity.id),
        "lead_id": str(activity.lead_id),
        "activity_type": activity.activity_type,
        "new_value": activity.new_value,
    }
