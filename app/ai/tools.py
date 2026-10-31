"""Approved AI tools with schema validation (PRD §11.3)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.market import InvestmentInput
from app.services.investment import calculate_investment
from app.services.market_analytics import price_analysis
from app.services.neighbourhood import get_neighbourhood
from app.services.properties import get_listing_for_property, search_properties, to_detail


def search_properties_tool(db: Session, spec: dict[str, Any]) -> dict[str, Any]:
    resp = search_properties(
        db,
        purpose=spec.get("purpose"),
        locality=spec.get("locality"),
        city=(spec.get("geographic_areas") or [None])[0] if spec.get("geographic_areas") else spec.get("city"),
        min_price=Decimal(str(spec["min_price"])) if spec.get("min_price") else None,
        max_price=Decimal(str(spec["max_price"])) if spec.get("max_price") else None,
        bedrooms=spec.get("bedrooms"),
        property_type=spec.get("property_type"),
        configuration=spec.get("configuration"),
        page=1,
        page_size=min(int(spec.get("page_size") or 10), 20),
    )
    return {
        "count": resp.pagination.total,
        "results": [r.model_dump(mode="json") for r in resp.results],
        "matching_reasons": ["hard_constraints_applied"],
    }


def get_property_details_tool(db: Session, property_id: str) -> dict[str, Any]:
    listing = get_listing_for_property(db, UUID(property_id))
    if not listing:
        return {"error": "Property not found or not published.", "property_id": property_id}
    return to_detail(db, listing).model_dump(mode="json")


def get_nearby_amenities_tool(
    db: Session, property_id: str, categories: list[str] | None = None, radius_m: float = 3000
) -> dict[str, Any]:
    data = get_neighbourhood(db, UUID(property_id), radius_m=radius_m, categories=categories)
    return data.model_dump(mode="json")


def get_price_benchmarks_tool(db: Session, property_id: str) -> dict[str, Any]:
    return price_analysis(db, UUID(property_id)).model_dump(mode="json")


def compare_properties_tool(db: Session, property_ids: list[str]) -> dict[str, Any]:
    ids = property_ids[:4]
    rows = []
    missing = []
    for pid in ids:
        listing = get_listing_for_property(db, UUID(pid))
        if not listing:
            missing.append(pid)
            continue
        rows.append(to_detail(db, listing).model_dump(mode="json"))
    return {
        "properties": rows,
        "missing_ids": missing,
        "definitions": {
            "price": "asking_price for buy / monthly_rent for rent",
            "area": "prefer super_built_up, else built_up, else carpet — never mix silently",
        },
    }


def calculate_investment_scenario_tool(inputs: dict[str, Any]) -> dict[str, Any]:
    payload = InvestmentInput(**inputs)
    return calculate_investment(payload).model_dump(mode="json")
