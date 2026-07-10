from fastapi import APIRouter
import clickhouse_connect
from src.core.config import settings

router = APIRouter()

@router.get("/summary", tags=["Analytics Dashboard"])
async def get_dashboard_summary():
    try:
        # Connect to ClickHouse safely
        client = clickhouse_connect.get_client(
            host="localhost", 
            port=8123,
            username="default",
            password=settings.CLICKHOUSE_PASSWORD
        )
        
        # Run a lightning-fast aggregation query
        stats = client.query("""
            SELECT 
                count() as total_requests,
                round(avg(latency_ms), 2) as avg_latency,
                sum(cache_hit) as total_hits,
                sum(total_tokens) as total_tokens,
                round(sum(estimated_cost), 6) as total_cost
            FROM gateway_logs
        """).result_rows

        # Fetch model comparison data
        models = client.query("""
            SELECT 
                model, 
                count() as requests, 
                round(avg(latency_ms), 2) as avg_latency
            FROM gateway_logs 
            GROUP BY model
        """).result_rows

        if not stats or not stats[0]:
            return {"error": "No data"}

        row = stats[0]
        total = row[0]
        hits = row[2] if row[2] else 0

        # Format model data for Recharts
        model_distribution = [{"name": m[0], "requests": m[1], "latency": m[2]} for m in models]

        return {
            "total_requests": total,
            "average_latency_ms": row[1] if row[1] else 0,
            "cache_hit_rate_percent": round((hits / total * 100), 1) if total > 0 else 0.0,
            "total_tokens": row[3] if row[3] else 0,
            "total_cost": row[4] if row[4] else 0.0,
            "models": model_distribution
        }
    except Exception as e:
        return {"error": str(e)}