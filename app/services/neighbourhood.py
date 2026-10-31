"""Neighbourhood intelligence services (PRD GEO-001 / GEO-002)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.amenity import Amenity
from app.models.geo import GeographicArea
from app.models.property import Property
from app.schemas.neighbourhood import AmenityOut, DistanceInfo, NeighbourhoodResponse
from app.services.geo import estimate_road_distance_m, haversine_m


CATEGORY_ALIASES = {
    "school": "school",
    "hospital": "hospital",
    "metro": "metro",
    "grocery": "grocery",
    "park": "park",
    "shopping": "shopping",
    "office": "office",
    "bank": "bank",
}


def get_neighbourhood(
    db: Session,
    property_id: UUID,
    *,
    radius_m: float = 3000,
    categories: list[str] | None = None,
) -> NeighbourhoodResponse:
    prop = db.get(Property, property_id)
    if not prop:
        raise APIError(404, "NOT_FOUND", "Property not found.")

    limitations: list[str] = []
    if prop.lat is None or prop.lng is None:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Property has no coordinates for neighbourhood search.",
            {"coordinates": ["Missing lat/lng"]},
        )

    cats = None
    if categories:
        cats = [CATEGORY_ALIASES.get(c.strip().lower(), c.strip().lower()) for c in categories if c.strip()]

    amenities_q = db.query(Amenity)
    if cats:
        amenities_q = amenities_q.filter(Amenity.category.in_(cats))

    results: list[AmenityOut] = []
    for amenity in amenities_q.all():
        straight = haversine_m(prop.lat, prop.lng, amenity.lat, amenity.lng)
        if straight > radius_m:
            continue
        road = estimate_road_distance_m(straight)
        results.append(
            AmenityOut(
                id=amenity.id,
                name=amenity.name,
                category=amenity.category,
                distance=DistanceInfo(value=road, unit="m", method="road_estimate"),
                source=amenity.provider_name,
                source_updated_at=amenity.source_updated_at,
                operational_status=amenity.operational_status,
                lat=amenity.lat,
                lng=amenity.lng,
            )
        )

    results.sort(key=lambda a: a.distance.value)
    loc = db.get(GeographicArea, prop.locality_id)
    coverage = loc.coverage_level if loc else "minimal"
    if coverage != "full":
        limitations.append("Amenity coverage is incomplete for this locality.")
    limitations.append("Road distances are estimates (straight-line × 1.35), not live routing.")
    limitations.append("Operational status is not independently verified unless stated.")

    profile = {
        "locality_name": loc.name if loc else None,
        "coverage_level": coverage,
        "fact_types": {
            "verified_facts": ["locality name", "seed amenity coordinates"],
            "derived_calculations": ["straight-line and estimated road distance"],
            "ai_generated_summaries": [],
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    return NeighbourhoodResponse(
        property_id=property_id,
        data_as_of=datetime.now(timezone.utc),
        coverage=coverage,
        amenities=results[:50],
        locality_profile=profile,
        limitations=limitations,
    )
