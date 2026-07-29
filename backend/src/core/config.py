from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "Enterprise AI Gateway"
    DEBUG: bool = False
    PORT: int = 8000

    INTERNAL_API_KEY: str = "secret-internal-key-123"

    
    GEMINI_API_KEY: str = Field(..., validation_alias="GEMINI_API_KEY")
    GROQ_API_KEY: str = Field(..., validation_alias="GROQ_API_KEY")
    
    REDIS_URL: str = "redis://localhost:6379/0"
    CLICKHOUSE_HOST: str = "localhost"

    CLICKHOUSE_PASSWORD: str = "gateway_secure_123"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()