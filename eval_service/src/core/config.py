from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GATEWAY_URL: str = "http://localhost:8000"
    INTERNAL_API_KEY: str = "secret-internal-key-123"
    
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PASSWORD: str = "gateway_secure_123"
    
    JUDGE_MODEL: str = "gemini-2.5-flash"
    JUDGE_PROVIDER: str = "google"

settings = Settings()
