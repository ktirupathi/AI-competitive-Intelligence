"""Routes package."""

from fastapi import APIRouter

from .admin import router as admin_router
from .alerts import router as alerts_router
from .auth import router as auth_router
from .billing import router as billing_router
from .briefings import router as briefings_router
from .competitors import router as competitors_router
from .insights import router as insights_router
from .integrations import router as integrations_router
from .metrics import router as metrics_router
from .public import router as public_router
from .search import router as search_router
from .settings import router as settings_router
from .workspaces import router as workspaces_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(competitors_router, prefix="/competitors", tags=["competitors"])
api_router.include_router(briefings_router, prefix="/briefings", tags=["briefings"])
api_router.include_router(insights_router, prefix="/insights", tags=["insights"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(public_router, prefix="/public", tags=["public"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
