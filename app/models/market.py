"""Market analytics and investment scenarios."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


class MarketObservation(Base):
    __tablename__ = "market_observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locality_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geographic_areas.id"), index=True)
    property_type: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)  # asking|transaction|rent|index
    area_basis: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    observation_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    observation_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    methodology_version: Mapped[str] = mapped_column(String(32), default="v1")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComparableSet(Base):
    __tablename__ = "comparable_sets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_property_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    search_specification: Mapped[dict] = mapped_column(JSON, default=dict)
    methodology_version: Mapped[str] = mapped_column(String(32), default="v1")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data_coverage: Mapped[str] = mapped_column(String(32), default="partial")
    status: Mapped[str] = mapped_column(String(32), default="ready")


class ComparableRecord(Base):
    __tablename__ = "comparable_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comparable_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comparable_sets.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listings.id", ondelete="SET NULL"), nullable=True
    )
    market_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("market_observations.id", ondelete="SET NULL"), nullable=True
    )
    inclusion_reason: Mapped[str] = mapped_column(String(255), default="similar_configuration")
    exclusion_or_adjustment_notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    relative_similarity_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)


class InvestmentScenario(Base):
    __tablename__ = "investment_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    input_parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    calculation_version: Mapped[str] = mapped_column(String(32), default="v1")
    results: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
