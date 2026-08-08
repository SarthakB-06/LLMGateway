import json
import asyncio
import numpy as np
from google import genai
from redisvl.schema import IndexSchema
from redisvl.index import AsyncSearchIndex
from redisvl.query import VectorQuery
from src.core.config import settings

class CacheService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.distance_threshold = 0.35 
        self._initialized = False
        self._lock = asyncio.Lock()
        self.index = None

    async def _get_embedding(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model='gemini-embedding-001',
            contents=text,
        )
        return [float(val) for val in response.embeddings[0].values]

    async def _setup_index(self, sample_vector: list[float]):
        """Dynamically creates the index based on the EXACT dimensions of the API response."""
        async with self._lock:
            if not self._initialized:
                dims = len(sample_vector)
                print(f"\n [SYSTEM] Initializing Redis Vector Index with {dims} dimensions...")
                
                schema_dict = {
                    "index": {
                        "name": "semantic_cache", 
                        "prefix": "cache",
                        "storage_type": "hash"  # Reverting to rock-solid Hash storage
                    },
                    "fields": [
                        {"name": "prompt", "type": "text"},
                        {"name": "response", "type": "text"},
                        {
                            "name": "embedding",
                            "type": "vector",
                            "attrs": {
                                "dims": dims,  # 🔥 Guarantees a 100% match with the vector size
                                "distance_metric": "cosine",
                                "algorithm": "flat",
                                "datatype": "float32"
                            }
                        }
                    ]
                }
                
                schema = IndexSchema.from_dict(schema_dict)
                self.index = AsyncSearchIndex(schema, redis_url=settings.REDIS_URL)
                try:
                    # Wipes out all previous broken JSON attempts
                    await self.index.create(overwrite=True, drop=True)
                except Exception as e:
                    # Ignore 'Index already exists' if another worker won the race right before lock
                    if "already exists" not in str(e).lower():
                        raise
                self._initialized = True

    async def get_response(self, model: str, prompt: str) -> dict | None:
        print(f"\n======== 📥 CACHE CHECK START ========")
        print(f"Checking cache for prompt: '{prompt}'")
        
        vector = await self._get_embedding(prompt)
        # Ensure index is built before checking
        await self._setup_index(vector)
        
        query = VectorQuery(
            vector=vector,
            vector_field_name="embedding",
            return_fields=["prompt", "response", "vector_distance"],
            num_results=1
        )
        
        try:
            results = await self.index.query(query)
        except Exception as e:
            # Index was lost (e.g. Redis restart). Reset so next call recreates it.
            print(f"⚠️ Cache index missing or unavailable ({e}). Resetting index.")
            self._initialized = False
            self.index = None
            return None
        print(f"Raw results from Redis: {results}")
        
        if results and len(results) > 0:
            distance = float(results[0]["vector_distance"])
            matched_prompt = results[0].get("prompt", "Unknown")
            print(f"🎯 Found potential match: '{matched_prompt}'")
            print(f"🔍 Distance: {distance} (Threshold is {self.distance_threshold})")
            
            if distance < self.distance_threshold:
                print("✅ SUCCESS: Within threshold! Serving Semantic Cache Hit.")
                cached_payload = json.loads(results[0]["response"])
                cached_payload["usage"]["cache_hit"] = True
                cached_payload["usage"]["cache_type"] = "semantic"
                return cached_payload
            else:
                print("❌ FAIL: Distance too high. Forcing live API call.")
        else:
            print("💭 Redis vector index returned 0 matches.")
            
        return None

    async def set_response(self, model: str, prompt: str, response_data: dict) -> None:
        print(f"\n======== 💾 SAVING TO CACHE ========")
        vector = await self._get_embedding(prompt)
        
        # Ensure index is built before saving
        await self._setup_index(vector)
        
        data = {
            "prompt": prompt,
            "response": json.dumps(response_data),
            # Hash storage requires bytes conversion via numpy
            "embedding": np.array(vector, dtype=np.float32).tobytes() 
        }
        
        keys = await self.index.load([data])
        print(f"💾 Successfully saved into Redis under Key: {keys}")
        print("=====================================\n")

cache_service = CacheService()