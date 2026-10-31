"""Geographic hierarchy and projects."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class GeographicArea(Base):
    __tablename__ = "geographic_areas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    area_type: Mapped[str] = mapped_column(String(32), nullable=False)  # city|locality|sector|...
    parent_area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("geographic_areas.id", ondelete="SET NULL"), nullable=True
    )
    canonical_slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_level: Mapped[str] = mapped_column(String(32), default="partial")  # full|partial|minimal
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    developer_organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True
    )
    locality_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geographic_areas.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    project_type: Mapped[str] = mapped_column(String(64), default="residential")
    construction_status: Mapped[str] = mapped_column(String(64), default="ready")
    possession_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_authority: Mapped[str | None] = mapped_column(String(128), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
