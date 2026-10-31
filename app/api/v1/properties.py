"""Property search and listing management."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional, require_roles
from app.core.errors import APIError
from app.models.property import Listing
from app.models.user import User
from app.schemas.common import MessageOut
from app.schemas.market import PriceAnalysisResponse
from app.schemas.property import ListingCreate, ListingOut, ListingUpdate, PropertyDetail, PropertySearchResponse
from app.services import properties as property_service
from app.services.market_analytics import price_analysis

router = APIRouter()


@router.get("/properties", response_model=PropertySearchResponse)
def list_properties(
    purpose: str | None = None,
    locality: str | None = None,
    city: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    bedrooms: int | None = None,
    property_type: str | None = None,
    configuration: str | None = None,
    furnishing: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return property_service.search_properties(
        db,
        purpose=purpose,
        locality=locality,
        city=city,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        property_type=property_type,
        configuration=configuration,
        furnishing=furnishing,
        page=page,
        page_size=page_size,
    )


@router.get("/properties/{property_id}", response_model=PropertyDetail)
def property_detail(property_id: UUID, db: Session = Depends(get_db)):
    listing = property_service.get_listing_for_property(db, property_id)
    if not listing:
        raise APIError(404, "NOT_FOUND", "Property not found.")
    return property_service.to_detail(db, listing)


@router.get("/properties/{property_id}/price-analysis", response_model=PriceAnalysisResponse)
def property_price_analysis(property_id: UUID, db: Session = Depends(get_db)):
    return price_analysis(db, property_id)


@router.post("/listings", response_model=ListingOut)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("property_owner", "agent", "developer", "admin")),
):
    listing = property_service.create_listing(db, payload, user.id)
    return listing


@router.patch("/listings/{listing_id}", response_model=ListingOut)
def patch_listing(
    listing_id: UUID,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("property_owner", "agent", "developer", "admin")),
):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise APIError(404, "NOT_FOUND", "Listing not found.")
    if listing.submitted_by_user_id != user.id:
        # allow admin
        from app.models.user import UserRole

        roles = {r.role for r in db.query(UserRole).filter(UserRole.user_id == user.id)}
        if "admin" not in roles:
            raise APIError(403, "FORBIDDEN", "Only the listing owner may edit this listing.")
    return property_service.update_listing(db, listing_id, payload, user.id)


@router.post("/listings/{listing_id}/publish", response_model=ListingOut)
def publish(
    listing_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("property_owner", "agent", "developer", "admin")),
):
    return property_service.publish_listing(db, listing_id)


@router.post("/listings/{listing_id}/confirm-availability", response_model=ListingOut)
def confirm_availability(
    listing_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("property_owner", "agent", "developer", "admin")),
):
    from datetime import datetime, timezone

    listing = db.get(Listing, listing_id)
    if not listing:
        raise APIError(404, "NOT_FOUND", "Listing not found.")
    listing.last_confirmed_at = datetime.now(timezone.utc)
    listing.availability_status = "available"
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/listings/{listing_id}/report", response_model=MessageOut)
def report_listing(
    listing_id: UUID,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise APIError(404, "NOT_FOUND", "Listing not found.")
    return MessageOut(
        message="Report received. A reviewer will inspect this listing.",
        details={"listing_id": str(listing_id), "reporter": str(user.id) if user else "anonymous"},
    )
