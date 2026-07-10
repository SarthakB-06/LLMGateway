from fastapi import FastAPI
from src.core.config import settings
from src.api.router import api_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise-grade architectural AI Gateway engine with Semantic Caching and Telemetry Ingestion.",
    version="1.0.0",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Vite's default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=settings.PORT, 
        reload=settings.DEBUG
    )