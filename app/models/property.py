"""Property identity and listing models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    locality_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geographic_areas.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    property_type: Mapped[str] = mapped_column(String(64), nullable=False)  # apartment|villa|plot|...
    configuration: Mapped[str] = mapped_column(String(32), nullable=False)  # 2BHK, 3BHK, ...
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carpet_area: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    built_up_area: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    super_built_up_area: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    area_unit: Mapped[str] = mapped_column(String(16), default="sq_ft")
    furnishing_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parking_details: Mapped[str | None] = mapped_column(String(128), nullable=True)
    floor_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amenities_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listings: Mapped[list[Listing]] = relationship(back_populates="property", cascade="all, delete-orphan")
    media: Mapped[list[PropertyMedia]] = relationship(back_populates="property", cascade="all, delete-orphan")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True
    )
    listing_purpose: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # buy|rent
    asking_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    monthly_rent: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    security_deposit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    availability_status: Mapped[str] = mapped_column(String(32), default="available", index=True)
    publication_status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="agent")
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    property: Mapped[Property] = relationship(back_populates="listings")


class ListingPriceHistory(Base):
    __tablename__ = "listing_price_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    new_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_source: Mapped[str] = mapped_column(String(64), default="manual")


class PropertyMedia(Base):
    __tablename__ = "property_media"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), default="image")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    property: Mapped[Property] = relationship(back_populates="media")
