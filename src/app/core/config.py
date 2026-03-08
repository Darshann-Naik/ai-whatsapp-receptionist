from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI WhatsApp Receptionist"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str = Field(...)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- ADD THESE THREE LINES ---
    META_ACCESS_TOKEN: str = Field(default="YOUR_META_TOKEN")
    META_VERIFY_TOKEN: str = Field(default="YOUR_VERIFY_TOKEN")
    GEMINI_API_KEY: str = Field(default="YOUR_GEMINI_KEY")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()