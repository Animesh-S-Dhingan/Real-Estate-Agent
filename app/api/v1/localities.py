from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.geo import GeographicArea
from app.schemas.neighbourhood import LocalityOut

router = APIRouter()


@router.get("/localities", response_model=list[LocalityOut])
def list_localities(
    city: str | None = None,
    area_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(GeographicArea)
    if area_type:
        q = q.filter(GeographicArea.area_type == area_type)
    if city:
        parent = (
            db.query(GeographicArea)
            .filter(
                GeographicArea.area_type == "city",
                GeographicArea.name.ilike(f"%{city}%"),
            )
            .first()
        )
        if parent:
            q = q.filter(GeographicArea.parent_area_id == parent.id)
    rows = q.order_by(GeographicArea.name).all()
    return [
        LocalityOut(
            id=r.id,
            name=r.name,
            slug=r.canonical_slug,
            area_type=r.area_type,
            coverage_level=r.coverage_level,
            center_lat=r.center_lat,
            center_lng=r.center_lng,
        )
        for r in rows
    ]
