import asyncio
from redis.asyncio import Redis
from src.core.config import settings

async def clear_redis():
    # Connect using your existing settings URL
    client = Redis.from_url(settings.REDIS_URL)
    print("🧹 Wiping all keys from Redis...")
    await client.flushall()
    print("✨ Redis database is completely empty!")
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(clear_redis())