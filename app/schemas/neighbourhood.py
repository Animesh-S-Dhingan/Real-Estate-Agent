"""Neighbourhood intelligence schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DistanceInfo(BaseModel):
    value: float
    unit: str = "m"
    method: str = "straight_line"


class AmenityOut(BaseModel):
    id: UUID
    name: str
    category: str
    distance: DistanceInfo
    source: str
    source_updated_at: datetime | None = None
    operational_status: str | None = None
    lat: float
    lng: float


class NeighbourhoodResponse(BaseModel):
    property_id: UUID
    data_as_of: datetime
    coverage: str
    amenities: list[AmenityOut]
    locality_profile: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class LocalityOut(BaseModel):
    id: UUID
    name: str
    slug: str
    area_type: str
    coverage_level: str
    center_lat: float | None = None
    center_lng: float | None = None
