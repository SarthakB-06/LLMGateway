"""
route.py — Quality-gated smart routing endpoint (Phase C2)
POST /api/v1/route
  { "prompt": str, "task_type": str = "general", "min_quality_threshold": float = 3.5 }
Calls eval_service /recommend to pick the best cost-quality model, then routes
through the existing internal completion logic. Falls back to a safe default if
eval_service is unreachable, times out, or has insufficient data.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import httpx
import time

from src.core.config import settings
from src.services.cache import cache_service
from src.services.telemetry import telemetry_service
from google import genai

router = APIRouter()
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
FALLBACK_MODEL    = "gemini-2.5-flash"
FALLBACK_PROVIDER = "google"
EVAL_TIMEOUT_S    = 2.0  

class RouteRequest(BaseModel):
    prompt: str
    task_type: Optional[str] = "general"
    min_quality_threshold: Optional[float] = 3.5

async def _ask_eval_service(task_type: str, threshold: float) -> Optional[str]:
    """
    Call eval_service /recommend. Returns the recommended model name or None
    if the service is unreachable, times out, or has insufficient data.
    """
    try:
        async with httpx.AsyncClient(timeout=EVAL_TIMEOUT_S) as client:
            resp = await client.post(f"{settings.EVAL_SERVICE_URL}/api/v1/recommend", 
                json={"task_type": task_type, "min_quality_threshold": threshold},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("recommended_model")
    except Exception:
        return None


async def _complete_via_google(prompt: str, background_tasks: BackgroundTasks) -> dict:
    """Thin wrapper around Gemini completion (mirrors internal.py logic)."""
    start = time.time()
    response = gemini_client.models.generate_content(
        model=FALLBACK_MODEL,
        contents=prompt,
    )
    response_text = response.text
    tokens_used = response.usage_metadata.total_token_count if response.usage_metadata else 0
    cost = (tokens_used / 1_000_000) * 0.15
    latency_ms = int((time.time() - start) * 1000)
    background_tasks.add_task(
        telemetry_service.log_usage,
        model=FALLBACK_MODEL,
        latency_ms=latency_ms,
        cache_hit=False,
        cache_type="",
        total_tokens=tokens_used,
        estimated_cost=cost,
    )
    return {
        "response": response_text,
        "latency_ms": latency_ms,
        "tokens": tokens_used,
        "cost": cost,
    }

@router.post("/route", tags=["Smart Routing"])
async def quality_gated_route(payload: RouteRequest, background_tasks: BackgroundTasks):
    """
    Quality-gated routing: asks eval_service for the best model by quality/cost,
    then routes the prompt. Falls back to gemini-2.5-flash on any failure.
    """

    start = time.time()

    # Cache is always optional — treat any Redis error as a miss
    try:
        cached = await cache_service.get_response(FALLBACK_MODEL, payload.prompt)
    except Exception:
        cached = None
    if cached:
        latency_ms = int((time.time() - start) * 1000)
        saved_tokens = cached.get("usage", {}).get("total_tokens", 0)
        background_tasks.add_task(
            telemetry_service.log_usage,
            model=FALLBACK_MODEL,
            latency_ms=latency_ms,
            cache_hit=True,
            cache_type=cached["usage"].get("cache_type", "semantic"),
            total_tokens=saved_tokens,
            estimated_cost=0.0,
        )
        content = cached["choices"][0]["message"]["content"]
        return {
            "response": content,
            "model_used": FALLBACK_MODEL,
            "routing_source": "cache",
            "latency_ms": latency_ms,
        }
    
    recommended_model = await _ask_eval_service(
        task_type=payload.task_type,
        threshold=payload.min_quality_threshold
    )

    routing_source = "eval_recommendation" if recommended_model else "fallback"
    model_to_use = recommended_model or FALLBACK_MODEL

    try:
        response = gemini_client.models.generate_content(
            model=model_to_use,
            contents=payload.prompt,
        )
        response_text = response.text
        tokens_used = response.usage_metadata.total_token_count if response.usage_metadata else 0
        cost = (tokens_used / 1_000_000) * 0.15
        latency_ms = int((time.time() - start) * 1000)
        # Cache the result
        cache_payload = {
            "model": model_to_use,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": response_text}}],
            "usage": {"cache_hit": False, "cache_type": None, "total_tokens": tokens_used},
        }
        try:
            await cache_service.set_response(model_to_use, payload.prompt, cache_payload)
        except Exception:
            pass  # cache write failure is non-fatal
        background_tasks.add_task(
            telemetry_service.log_usage,
            model=model_to_use,
            latency_ms=latency_ms,
            cache_hit=False,
            cache_type="",
            total_tokens=tokens_used,
            estimated_cost=cost,
        )
        return {
            "response": response_text,
            "model_used": model_to_use,
            "routing_source": routing_source,
            "latency_ms": latency_ms,
            "tokens": tokens_used,
            "cost": cost,
        }
    except Exception as e:
        if model_to_use != FALLBACK_MODEL:
            result = await _complete_via_google(payload.prompt, background_tasks)
            return {**result, "model_used": FALLBACK_MODEL, "routing_source": "fallback_on_error"}
        raise HTTPException(status_code=500, detail=f"Route completion error: {str(e)}")

