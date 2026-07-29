from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from core.config import settings
from services.cache import cache_service
from services.telemetry import telemetry_service
from google import genai
from groq import Groq
import time


router = APIRouter()


gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
groq_client = Groq(api_key=settings.GROQ_API_KEY)

class InternalCompletionRequest(BaseModel):
    provider: str # "google" or "groq"
    model: str
    prompt: str
    response_format: Optional[dict] = None # For JSON mode (used by judge)




def verify_internal_key(x_internal_key: str = Header(...)):
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid Internal Key")
    return x_internal_key

@router.post("/internal/complete", tags=["Internal"])
async def internal_complete(
    payload: InternalCompletionRequest, 
    background_tasks: BackgroundTasks,
    key: str = Depends(verify_internal_key)
):
    start_time = time.time()
    try:
        # 1. Check Cache
        cached_response = await cache_service.get_response(payload.model, payload.prompt)
        if cached_response:
            latency_ms = int((time.time() - start_time) * 1000)
            saved_tokens = cached_response.get("usage", {}).get("total_tokens", 0)
            
            # Extract content from cached standard format
            content = cached_response["choices"][0]["message"]["content"]
            
            background_tasks.add_task(
                telemetry_service.log_usage,
                model=payload.model,
                latency_ms=latency_ms,
                cache_hit=True,
                cache_type=cached_response["usage"]["cache_type"],
                total_tokens=saved_tokens,
                estimated_cost=0.0 
            )
            return {
                "response": content,
                "latency_ms": latency_ms,
                "tokens": saved_tokens,
                "cost": 0.0,
                "cache_hit": True
            }
        # 2. Call Provider
        if payload.provider == "google":
            # Pass response_format if provided (e.g. for JSON structured output)
            config_kwargs = {}
            if payload.response_format:
                config_kwargs["response_mime_type"] = "application/json"
                # If a specific schema is needed, you could pass it to response_schema here
            response = gemini_client.models.generate_content(
                model=payload.model,
                contents=payload.prompt,
                config=config_kwargs if config_kwargs else None
            )
            response_text = response.text
            tokens_used = response.usage_metadata.total_token_count if response.usage_metadata else 0
            cost = (tokens_used / 1000000) * 0.15 
            
        elif payload.provider == "groq":
            kwargs = {
                "messages": [{"role": "user", "content": payload.prompt}],
                "model": payload.model,
            }
            if payload.response_format and payload.response_format.get("type") == "json_object":
                kwargs["response_format"] = {"type": "json_object"}
                
            response = groq_client.chat.completions.create(**kwargs)
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            cost = (tokens_used / 1000000) * 0.05
        else:
            raise ValueError(f"Unknown provider: {payload.provider}")
        
        # 3. Cache and Telemetry
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Standardize for cache
        cache_payload = {
            "model": payload.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": response_text}}],
            "usage": {"cache_hit": False, "cache_type": None, "total_tokens": tokens_used}
        }
        await cache_service.set_response(payload.model, payload.prompt, cache_payload)
        
        background_tasks.add_task(
            telemetry_service.log_usage,
            model=payload.model,
            latency_ms=latency_ms,
            cache_hit=False,
            cache_type="",
            total_tokens=tokens_used,
            estimated_cost=cost
        )
        return {
            "response": response_text,
            "latency_ms": latency_ms,
            "tokens": tokens_used,
            "cost": cost,
            "cache_hit": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal completion error: {str(e)}")