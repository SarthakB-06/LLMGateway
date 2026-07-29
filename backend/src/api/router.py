from fastapi import APIRouter
from api.v1 import health
from api.v1 import chat
from api.v1 import analytics
from api.v1 import internal
api_router = APIRouter()

# Include versioned routers under the /v1 prefix
api_router.include_router(health.router, prefix="/v1")
api_router.include_router(chat.router, prefix="/v1")
api_router.include_router(analytics.router, prefix="/v1")
api_router.include_router(internal.router)