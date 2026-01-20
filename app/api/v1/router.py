from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import verify_api_key
from app.api.v1.endpoints import activities, buildings, organizations


api_router = APIRouter(dependencies=[Depends(verify_api_key)])

api_router.include_router(buildings.router, tags=["buildings"])
api_router.include_router(organizations.router, tags=["organizations"])
api_router.include_router(activities.router, tags=["activities"])
