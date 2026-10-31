"""Amenities and data provenance."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    terms_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    permitted_storage_policy: Mapped[str] = mapped_column(String(128), default="restricted")
    permitted_display_policy: Mapped[str] = mapped_column(String(128), default="attribution_required")
    attribution_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_status: Mapped[str] = mapped_column(String(32), default="active")


class Amenity(Base):
    __tablename__ = "amenities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_name: Mapped[str] = mapped_column(String(64), default="seed")
    provider_place_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    operational_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
