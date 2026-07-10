from fastapi import APIRouter
from src.core.config import settings

router = APIRouter()

@router.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": "debug" if settings.DEBUG else "production"
    }