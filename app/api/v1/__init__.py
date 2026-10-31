from fastapi import APIRouter

from app.api.v1 import ai, auth, investment, leads, localities, neighbourhood, properties

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(properties.router, tags=["properties"])
api_router.include_router(neighbourhood.router, tags=["neighbourhood"])
api_router.include_router(localities.router, tags=["localities"])
api_router.include_router(investment.router, tags=["investment"])
api_router.include_router(leads.router, tags=["leads"])
api_router.include_router(ai.router, tags=["ai"])
