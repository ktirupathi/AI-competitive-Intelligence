"""Routes package."""

from fastapi import APIRouter

from .auth import router as auth_router
from .billing import router as billing_router
from .briefings import router as briefings_router
from .competitors import router as competitors_router
from .insights import router as insights_router
from .integrations import router as integrations_router
from .settings import router as settings_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(competitors_router, prefix="/competitors", tags=["competitors"])
api_router.include_router(briefings_router, prefix="/briefings", tags=["briefings"])
api_router.include_router(insights_router, prefix="/insights", tags=["insights"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
