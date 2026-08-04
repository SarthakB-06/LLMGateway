from fastapi import FastAPI
from src.api.v1.router import router as v1_router
from src.services.clickhouse_writer import clickhouse_writer
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Eval Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Initialize ClickHouse connection and table
    clickhouse_writer.connect()

app.include_router(v1_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}
