from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.neighbourhood import NeighbourhoodResponse
from app.services.neighbourhood import get_neighbourhood

router = APIRouter()


@router.get("/properties/{property_id}/neighbourhood", response_model=NeighbourhoodResponse)
def neighbourhood(
    property_id: UUID,
    radius_m: float = Query(3000, ge=100, le=15000),
    categories: str | None = Query(None, description="Comma-separated: school,hospital,metro,..."),
    db: Session = Depends(get_db),
):
    cats = [c.strip() for c in categories.split(",")] if categories else None
    return get_neighbourhood(db, property_id, radius_m=radius_m, categories=cats)
