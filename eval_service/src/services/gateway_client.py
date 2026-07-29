import httpx
from src.core.config import settings

class GatewayClient:
    def __init__(self):
        self.base_url = settings.GATEWAY_URL
        self.headers = {"X-Internal-Key": settings.INTERNAL_API_KEY}
        
    async def complete(self, provider: str, model: str, prompt: str, json_mode: bool = False):
        payload = {
            "provider": provider,
            "model": model,
            "prompt": prompt
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/complete",
                headers=self.headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

gateway_client = GatewayClient()
