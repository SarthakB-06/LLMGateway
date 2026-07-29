from fastapi import FastAPI
from api.v1.router import router as v1_router
from services.clickhouse_writer import clickhouse_writer

app = FastAPI(title="Eval Service", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    # Initialize ClickHouse connection and table
    clickhouse_writer.connect()

app.include_router(v1_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}
