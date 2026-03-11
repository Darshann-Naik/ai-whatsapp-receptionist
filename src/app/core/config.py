from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI WhatsApp Receptionist"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str = "0514942a1a897392d6acc5240b6905521cdd7e94678fb39e91e81c51493d4a7"  # Default fallback added to prevent crash
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- META & AI TOKENS ---
    # We removed the defaults! Now FastAPI MUST read these from your .env file
    META_ACCESS_TOKEN: str
    META_VERIFY_TOKEN: str
    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True, 
        extra="ignore"
    )

settings = Settings()