"""Lead creation and agent inbox."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.lead import Lead, LeadActivity
from app.models.property import Listing
from app.models.user import User
from app.schemas.lead import LeadActivityCreate, LeadCreate, LeadUpdate


def create_lead(db: Session, payload: LeadCreate, user: User | None, idempotency_key: str | None) -> Lead:
    key = payload.idempotency_key or idempotency_key
    if key:
        existing = db.query(Lead).filter(Lead.idempotency_key == key).first()
        if existing:
            return existing

    listing = db.get(Listing, payload.listing_id)
    if not listing or listing.publication_status != "published":
        raise APIError(404, "NOT_FOUND", "Listing not available for enquiry.")

    lead = Lead(
        listing_id=payload.listing_id,
        requester_user_id=user.id if user else None,
        assigned_agent_id=listing.submitted_by_user_id,
        organisation_id=listing.organisation_id,
        message=payload.message,
        contact_preference=payload.contact_preference,
        requester_name=payload.requester_name or (user.full_name if user else None),
        requester_email=payload.requester_email or (user.email if user else None),
        requester_phone=payload.requester_phone or (user.phone if user else None),
        status="new",
        idempotency_key=key,
    )
    db.add(lead)
    db.flush()
    db.add(
        LeadActivity(
            lead_id=lead.id,
            actor_user_id=user.id if user else None,
            activity_type="created",
            new_value="new",
        )
    )
    db.commit()
    db.refresh(lead)
    return lead


def list_agent_leads(db: Session, agent: User, status: str | None = None) -> list[Lead]:
    q = db.query(Lead).filter(
        (Lead.assigned_agent_id == agent.id) | (Lead.requester_user_id == agent.id)
    )
    # Prefer assigned leads for agents
    q = db.query(Lead).filter(Lead.assigned_agent_id == agent.id)
    if status:
        q = q.filter(Lead.status == status)
    return q.order_by(Lead.created_at.desc()).all()


def update_lead(db: Session, lead_id: UUID, payload: LeadUpdate, actor: User) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise APIError(404, "NOT_FOUND", "Lead not found.")
    if lead.assigned_agent_id != actor.id:
        from app.models.user import UserRole

        roles = {r.role for r in db.query(UserRole).filter(UserRole.user_id == actor.id).all()}
        if "admin" not in roles:
            raise APIError(403, "FORBIDDEN", "Not authorised for this lead.")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        old = getattr(lead, field)
        setattr(lead, field, value)
        if field == "status" and old != value:
            db.add(
                LeadActivity(
                    lead_id=lead.id,
                    actor_user_id=actor.id,
                    activity_type="status_change",
                    previous_value=old,
                    new_value=value,
                )
            )
    db.commit()
    db.refresh(lead)
    return lead


def add_activity(db: Session, lead_id: UUID, payload: LeadActivityCreate, actor: User) -> LeadActivity:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise APIError(404, "NOT_FOUND", "Lead not found.")
    if lead.assigned_agent_id != actor.id and lead.requester_user_id != actor.id:
        raise APIError(403, "FORBIDDEN", "Not authorised for this lead.")
    activity = LeadActivity(
        lead_id=lead.id,
        actor_user_id=actor.id,
        activity_type=payload.activity_type,
        new_value=payload.new_value,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity
