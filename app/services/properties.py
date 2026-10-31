"""Property search, listing lifecycle, and serializers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import APIError
from app.models.geo import GeographicArea
from app.models.property import Listing, ListingPriceHistory, Property
from app.schemas.common import AreaValue, PaginationMeta
from app.schemas.property import ListingCreate, ListingUpdate, PropertyCard, PropertyDetail, PropertySearchResponse

settings = get_settings()


def _area_payload(prop: Property) -> AreaValue:
    if prop.super_built_up_area is not None:
        return AreaValue(value=str(prop.super_built_up_area), unit=prop.area_unit, basis="super_built_up")
    if prop.built_up_area is not None:
        return AreaValue(value=str(prop.built_up_area), unit=prop.area_unit, basis="built_up")
    if prop.carpet_area is not None:
        return AreaValue(value=str(prop.carpet_area), unit=prop.area_unit, basis="carpet")
    return AreaValue(value=None, unit=prop.area_unit, basis=None)


def _locality_name(db: Session, locality_id: UUID) -> tuple[str, str | None]:
    loc = db.get(GeographicArea, locality_id)
    if not loc:
        return ("Unknown", None)
    city = None
    if loc.parent_area_id:
        parent = db.get(GeographicArea, loc.parent_area_id)
        city = parent.name if parent else None
    return loc.name, city


def to_card(db: Session, listing: Listing, reasons: list[str] | None = None) -> PropertyCard:
    prop = listing.property
    locality, city = _locality_name(db, prop.locality_id)
    return PropertyCard(
        id=prop.id,
        listing_id=listing.id,
        title=prop.title,
        purpose=listing.listing_purpose,
        asking_price=str(listing.asking_price) if listing.asking_price is not None else None,
        monthly_rent=str(listing.monthly_rent) if listing.monthly_rent is not None else None,
        currency=listing.currency,
        area=_area_payload(prop),
        locality=locality,
        city=city,
        configuration=prop.configuration,
        property_type=prop.property_type,
        bedrooms=prop.bedrooms,
        availability_status=listing.availability_status,
        publication_status=listing.publication_status,
        source_type=listing.source_type,
        lat=prop.lat,
        lng=prop.lng,
        last_confirmed_at=listing.last_confirmed_at,
        match_reasons=reasons or [],
    )


def to_detail(db: Session, listing: Listing) -> PropertyDetail:
    card = to_card(db, listing)
    prop = listing.property
    tags = [t.strip() for t in (prop.amenities_tags or "").split(",") if t.strip()]
    limitations = []
    loc = db.get(GeographicArea, prop.locality_id)
    if loc and loc.coverage_level != "full":
        limitations.append(
            f"Locality coverage is '{loc.coverage_level}' — neighbourhood scores may be incomplete."
        )
    if prop.lat is None or prop.lng is None:
        limitations.append("Property coordinates are missing; map and distance features are limited.")
    return PropertyDetail(
        **card.model_dump(),
        address=prop.address,
        bathrooms=prop.bathrooms,
        carpet_area=str(prop.carpet_area) if prop.carpet_area is not None else None,
        built_up_area=str(prop.built_up_area) if prop.built_up_area is not None else None,
        super_built_up_area=str(prop.super_built_up_area) if prop.super_built_up_area is not None else None,
        furnishing_status=prop.furnishing_status,
        parking_details=prop.parking_details,
        floor_number=prop.floor_number,
        total_floors=prop.total_floors,
        description=listing.description,
        amenities_tags=tags,
        media=[m.storage_key for m in prop.media],
        limitations=limitations,
    )


def search_properties(
    db: Session,
    *,
    purpose: str | None = None,
    locality: str | None = None,
    city: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    bedrooms: int | None = None,
    property_type: str | None = None,
    furnishing: str | None = None,
    configuration: str | None = None,
    page: int = 1,
    page_size: int = 20,
    include_inactive: bool = False,
) -> PropertySearchResponse:
    if page < 1 or page_size < 1 or page_size > 100:
        raise APIError(400, "VALIDATION_ERROR", "Invalid pagination.", {"page": ["Must be >= 1"], "page_size": ["1-100"]})

    q = (
        db.query(Listing)
        .join(Property, Listing.property_id == Property.id)
        .options(joinedload(Listing.property))
    )

    if not include_inactive:
        q = q.filter(
            Listing.publication_status == "published",
            Listing.availability_status.in_(["available", "pending"]),
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.listing_freshness_days)
        q = q.filter(or_(Listing.expires_at.is_(None), Listing.expires_at > datetime.now(timezone.utc)))
        # Soft freshness: prefer confirmed; still show others (ranking later)
        _ = cutoff

    reasons_base: list[str] = []
    if purpose:
        if purpose not in {"buy", "rent"}:
            raise APIError(400, "VALIDATION_ERROR", "Invalid purpose.", {"purpose": ["Must be buy or rent"]})
        q = q.filter(Listing.listing_purpose == purpose)
        reasons_base.append(f"purpose={purpose}")

    if locality:
        loc_ids = [
            r.id
            for r in db.query(GeographicArea)
            .filter(
                or_(
                    GeographicArea.canonical_slug.ilike(f"%{locality.lower()}%"),
                    GeographicArea.name.ilike(f"%{locality}%"),
                )
            )
            .all()
        ]
        if not loc_ids:
            return PropertySearchResponse(
                results=[],
                pagination=PaginationMeta(page=page, page_size=page_size, total=0),
            )
        q = q.filter(Property.locality_id.in_(loc_ids))
        reasons_base.append(f"locality~{locality}")

    if city:
        cities = (
            db.query(GeographicArea)
            .filter(
                GeographicArea.area_type == "city",
                or_(
                    GeographicArea.canonical_slug.ilike(f"%{city.lower()}%"),
                    GeographicArea.name.ilike(f"%{city}%"),
                ),
            )
            .all()
        )
        child_ids = []
        for c in cities:
            child_ids.extend(
                [a.id for a in db.query(GeographicArea).filter(GeographicArea.parent_area_id == c.id).all()]
            )
            child_ids.append(c.id)
        if not child_ids:
            return PropertySearchResponse(
                results=[],
                pagination=PaginationMeta(page=page, page_size=page_size, total=0),
            )
        q = q.filter(Property.locality_id.in_(child_ids))
        reasons_base.append(f"city~{city}")

    if bedrooms is not None:
        q = q.filter(Property.bedrooms == bedrooms)
        reasons_base.append(f"bedrooms={bedrooms}")
    if property_type:
        q = q.filter(Property.property_type.ilike(property_type))
        reasons_base.append(f"type={property_type}")
    if configuration:
        q = q.filter(Property.configuration.ilike(configuration))
        reasons_base.append(f"config={configuration}")
    if furnishing:
        q = q.filter(Property.furnishing_status.ilike(f"%{furnishing}%"))

    if min_price is not None or max_price is not None:
        price_col = Listing.asking_price
        # For rent searches prefer monthly_rent
        if purpose == "rent":
            price_col = Listing.monthly_rent
        if min_price is not None:
            if min_price <= 0:
                raise APIError(400, "VALIDATION_ERROR", "Invalid min_price.", {"min_price": ["Must be > 0"]})
            q = q.filter(price_col >= min_price)
            reasons_base.append(f"min_price={min_price}")
        if max_price is not None:
            if max_price <= 0:
                raise APIError(400, "VALIDATION_ERROR", "Invalid max_price.", {"max_price": ["Must be > 0"]})
            q = q.filter(price_col <= max_price)
            reasons_base.append(f"max_price={max_price}")

    total = q.count()
    rows = (
        q.order_by(Listing.published_at.desc(), Listing.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    results = [to_card(db, row, reasons_base) for row in rows]
    return PropertySearchResponse(
        results=results,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


def create_listing(db: Session, payload: ListingCreate, user_id: UUID | None) -> Listing:
    loc = (
        db.query(GeographicArea)
        .filter(
            or_(
                GeographicArea.canonical_slug == payload.locality_slug.lower(),
                GeographicArea.name.ilike(payload.locality_slug),
            )
        )
        .first()
    )
    if not loc:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Unknown locality.",
            {"locality_slug": ["Unrecognised locality — do not invent locations."]},
        )

    if payload.listing_purpose == "buy" and (payload.asking_price is None or payload.asking_price <= 0):
        raise APIError(400, "VALIDATION_ERROR", "Asking price required.", {"asking_price": ["Must be > 0"]})
    if payload.listing_purpose == "rent" and (payload.monthly_rent is None or payload.monthly_rent <= 0):
        raise APIError(400, "VALIDATION_ERROR", "Monthly rent required.", {"monthly_rent": ["Must be > 0"]})
    if not payload.description:
        raise APIError(400, "VALIDATION_ERROR", "Description required.", {"description": ["Required"]})

    prop = Property(
        project_id=payload.project_id,
        locality_id=loc.id,
        title=payload.title,
        address=payload.address,
        lat=payload.lat or loc.center_lat,
        lng=payload.lng or loc.center_lng,
        property_type=payload.property_type,
        configuration=payload.configuration,
        bedrooms=payload.bedrooms,
        bathrooms=payload.bathrooms,
        carpet_area=payload.carpet_area,
        built_up_area=payload.built_up_area,
        super_built_up_area=payload.super_built_up_area,
        area_unit=payload.area_unit,
        furnishing_status=payload.furnishing_status,
        parking_details=payload.parking_details,
        floor_number=payload.floor_number,
        total_floors=payload.total_floors,
        amenities_tags=",".join(payload.amenities_tags),
    )
    db.add(prop)
    db.flush()

    now = datetime.now(timezone.utc)
    listing = Listing(
        property_id=prop.id,
        submitted_by_user_id=user_id,
        organisation_id=payload.organisation_id,
        listing_purpose=payload.listing_purpose,
        asking_price=payload.asking_price,
        monthly_rent=payload.monthly_rent,
        security_deposit=payload.security_deposit,
        description=payload.description,
        source_type=payload.source_type,
        publication_status="published" if payload.publish else "draft",
        availability_status="available",
        published_at=now if payload.publish else None,
        last_confirmed_at=now if payload.publish else None,
        expires_at=now + timedelta(days=settings.listing_freshness_days) if payload.publish else None,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def update_listing(db: Session, listing_id: UUID, payload: ListingUpdate, user_id: UUID | None) -> Listing:
    listing = db.get(Listing, listing_id)
    if not listing:
        raise APIError(404, "NOT_FOUND", "Listing not found.")

    data = payload.model_dump(exclude_unset=True)
    price_fields = {"asking_price", "monthly_rent"}
    for field, value in data.items():
        if field in price_fields and value is not None:
            old = getattr(listing, field)
            if old != value:
                db.add(
                    ListingPriceHistory(
                        listing_id=listing.id,
                        previous_price=old,
                        new_price=value,
                        changed_by_user_id=user_id,
                        change_source="manual",
                    )
                )
        setattr(listing, field, value)
    db.commit()
    db.refresh(listing)
    return listing


def publish_listing(db: Session, listing_id: UUID) -> Listing:
    listing = (
        db.query(Listing).options(joinedload(Listing.property)).filter(Listing.id == listing_id).first()
    )
    if not listing:
        raise APIError(404, "NOT_FOUND", "Listing not found.")
    prop = listing.property
    missing = []
    if not prop.title:
        missing.append("title")
    if not listing.description:
        missing.append("description")
    if listing.listing_purpose == "buy" and not listing.asking_price:
        missing.append("asking_price")
    if listing.listing_purpose == "rent" and not listing.monthly_rent:
        missing.append("monthly_rent")
    if missing:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Cannot publish incomplete listing.",
            {m: ["Required before publish"] for m in missing},
        )
    now = datetime.now(timezone.utc)
    listing.publication_status = "published"
    listing.published_at = now
    listing.last_confirmed_at = now
    listing.expires_at = now + timedelta(days=settings.listing_freshness_days)
    db.commit()
    db.refresh(listing)
    return listing


def get_listing_for_property(db: Session, property_id: UUID) -> Listing | None:
    return (
        db.query(Listing)
        .options(joinedload(Listing.property))
        .filter(
            Listing.property_id == property_id,
            Listing.publication_status == "published",
        )
        .order_by(Listing.published_at.desc())
        .first()
    )
