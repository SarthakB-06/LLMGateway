from fastapi import APIRouter, HTTPException, BackgroundTasks
from google import genai
from src.core.config import settings
from src.services.cache import cache_service
from pydantic import BaseModel
from src.services.telemetry import telemetry_service
from groq import Groq
import time

router = APIRouter()
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
groq_client = Groq(api_key=settings.GROQ_API_KEY)

class ChatRequest(BaseModel):
    prompt: str
    model: str = "gemini-2.5-flash"

@router.post("/chat", tags=["AI Routing Engine"])
async def proxy_chat(payload: ChatRequest, background_tasks: BackgroundTasks):
    start_time = time.time()
    try:
        cached_response = await cache_service.get_response(payload.model, payload.prompt)
        if cached_response:
            latency_ms = (time.time() - start_time) * 1000

            saved_tokens = cached_response.get("usage", {}).get("total_tokens", 0)

            background_tasks.add_task(
                telemetry_service.log_usage,
                model=payload.model,
                latency_ms=latency_ms,
                cache_hit=True,
                cache_type=cached_response["usage"]["cache_type"],
                total_tokens=saved_tokens,
                estimated_cost=0.0 
            )
            # Mark tracking metrics as a successful cache hit
            cached_response["usage"]["cache_hit"] = True
            cached_response["usage"]["cache_type"] = "exact"
            return cached_response


        if "gemini" in payload.model.lower():
            # Route to Google
            response = gemini_client.models.generate_content(
                model=payload.model,
                contents=payload.prompt,
            )
            response_text = response.text
            tokens_used = response.usage_metadata.total_token_count if response.usage_metadata else 0
            # Gemini 1.5 Flash est. cost per 1M tokens
            cost = (tokens_used / 1000000) * 0.15 
            
        else:
            # Route to Groq (assuming LLaMA or Mixtral)
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": payload.prompt}],
                model=payload.model,
            )
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            # Groq LLaMA 3 8B est. cost per 1M tokens
            cost = (tokens_used / 1000000) * 0.05
        
        # Standardized return envelope
        response_payload = {
            "model": payload.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    }
                }
            ],
            "usage": {
                "cache_hit": False,
                "cache_type": None,
                "total_tokens": tokens_used,
            }
        }

    
        await cache_service.set_response(
            model=payload.model,
            prompt=payload.prompt,
            response_data=response_payload,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        background_tasks.add_task(
            telemetry_service.log_usage,
            model=payload.model,
            latency_ms=latency_ms,
            cache_hit=False,
            cache_type="",
            total_tokens=tokens_used,
            estimated_cost=cost
        )

        return response_payload

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Gateway routing exception: {str(e)}"
        )