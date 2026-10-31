"""Price analysis and comparable properties (PRD INV-001 / INV-002)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.core.errors import APIError
from app.models.market import MarketObservation
from app.models.property import Listing, Property
from app.schemas.market import PriceAnalysisResponse
from app.services.properties import get_listing_for_property


def _ppsqft(price: Decimal | None, area: Decimal | None) -> Decimal | None:
    if price is None or area is None or area <= 0:
        return None
    return (price / area).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def price_analysis(db: Session, property_id: UUID) -> PriceAnalysisResponse:
    listing = get_listing_for_property(db, property_id)
    if not listing:
        # also allow any listing for owner workflows
        listing = (
            db.query(Listing)
            .options(joinedload(Listing.property))
            .filter(Listing.property_id == property_id)
            .first()
        )
    if not listing:
        raise APIError(404, "NOT_FOUND", "No listing found for property.")

    prop = listing.property
    area = prop.super_built_up_area or prop.built_up_area or prop.carpet_area
    basis = (
        "super_built_up"
        if prop.super_built_up_area is not None
        else "built_up"
        if prop.built_up_area is not None
        else "carpet"
        if prop.carpet_area is not None
        else None
    )
    price = listing.asking_price if listing.listing_purpose == "buy" else listing.monthly_rent
    pps = _ppsqft(price, area)

    # Comparables: same locality + config + purpose
    comps = (
        db.query(Listing)
        .join(Property)
        .filter(
            Listing.id != listing.id,
            Listing.publication_status == "published",
            Listing.listing_purpose == listing.listing_purpose,
            Property.locality_id == prop.locality_id,
            Property.configuration == prop.configuration,
        )
        .limit(20)
        .all()
    )

    obs = (
        db.query(MarketObservation)
        .filter(
            MarketObservation.locality_id == prop.locality_id,
            MarketObservation.metric_name == "asking_price_per_sq_ft",
            MarketObservation.transaction_type == "asking",
        )
        .order_by(MarketObservation.observed_at.desc())
        .first()
    )

    limitations: list[str] = []
    benchmark: dict
    if obs and obs.sample_size and obs.sample_size >= 5:
        benchmark = {
            "value": str(obs.value),
            "metric": obs.metric_name,
            "sample_size": obs.sample_size,
            "period": {
                "start": str(obs.observation_period_start) if obs.observation_period_start else None,
                "end": str(obs.observation_period_end) if obs.observation_period_end else None,
            },
            "confidence": "moderate",
            "transaction_type": "asking",
            "note": "Asking-price observation — not a verified transaction.",
        }
    else:
        benchmark = {
            "value": None,
            "metric": "asking_price_per_sq_ft",
            "sample_size": obs.sample_size if obs else 0,
            "period": None,
            "confidence": "insufficient_data",
        }
        limitations.append("Insufficient comparable observations to produce a reliable benchmark.")

    if basis is None:
        limitations.append("No area value available; price-per-sqft cannot be computed.")
    if listing.listing_purpose == "rent":
        limitations.append("Price analysis for rent uses monthly rent / area when area is present.")

    formula = None
    if pps is not None and price is not None and area is not None:
        formula = f"{price} / {area} ({basis}) = {pps}"

    return PriceAnalysisResponse(
        listing_id=listing.id,
        asking_price=str(price) if price is not None else None,
        area_basis=basis,
        asking_price_per_sq_ft=str(pps) if pps is not None else None,
        benchmark=benchmark,
        comparables_count=len(comps),
        formula=formula,
        limitations=limitations,
    )
