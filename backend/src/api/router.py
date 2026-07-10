from fastapi import APIRouter
from src.api.v1 import health
from src.api.v1 import chat
from src.api.v1 import analytics

api_router = APIRouter()

# Include versioned routers under the /v1 prefix
api_router.include_router(health.router, prefix="/v1")
api_router.include_router(chat.router, prefix="/v1")
api_router.include_router(analytics.router, prefix="/v1")