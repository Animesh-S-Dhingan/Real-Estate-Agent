"""Property and listing schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import AreaValue, ORMModel, PaginatedResponse


class ListingCreate(BaseModel):
    title: str
    listing_purpose: str = Field(pattern="^(buy|rent)$")
    property_type: str
    configuration: str
    locality_slug: str
    address: str
    lat: float | None = None
    lng: float | None = None
    asking_price: Decimal | None = None
    monthly_rent: Decimal | None = None
    security_deposit: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    carpet_area: Decimal | None = None
    built_up_area: Decimal | None = None
    super_built_up_area: Decimal | None = None
    area_unit: str = "sq_ft"
    furnishing_status: str | None = None
    parking_details: str | None = None
    floor_number: int | None = None
    total_floors: int | None = None
    description: str | None = None
    source_type: str = "agent"
    amenities_tags: list[str] = Field(default_factory=list)
    project_id: UUID | None = None
    organisation_id: UUID | None = None
    publish: bool = False


class ListingUpdate(BaseModel):
    asking_price: Decimal | None = None
    monthly_rent: Decimal | None = None
    security_deposit: Decimal | None = None
    availability_status: str | None = None
    description: str | None = None
    furnishing_status: str | None = None
    parking_details: str | None = None


class PropertyCard(BaseModel):
    id: UUID
    listing_id: UUID
    title: str
    purpose: str
    asking_price: str | None = None
    monthly_rent: str | None = None
    currency: str = "INR"
    area: AreaValue
    locality: str
    city: str | None = None
    configuration: str
    property_type: str
    bedrooms: int | None = None
    availability_status: str
    publication_status: str
    source_type: str
    lat: float | None = None
    lng: float | None = None
    last_confirmed_at: datetime | None = None
    match_reasons: list[str] = Field(default_factory=list)


class PropertyDetail(PropertyCard):
    address: str
    bathrooms: int | None = None
    carpet_area: str | None = None
    built_up_area: str | None = None
    super_built_up_area: str | None = None
    furnishing_status: str | None = None
    parking_details: str | None = None
    floor_number: int | None = None
    total_floors: int | None = None
    description: str | None = None
    amenities_tags: list[str] = Field(default_factory=list)
    media: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ListingOut(ORMModel):
    id: UUID
    property_id: UUID
    listing_purpose: str
    asking_price: Decimal | None
    monthly_rent: Decimal | None
    availability_status: str
    publication_status: str
    description: str | None
    published_at: datetime | None


PropertySearchResponse = PaginatedResponse[PropertyCard]
