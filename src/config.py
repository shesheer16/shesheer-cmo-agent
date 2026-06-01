from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Intelligence Layer
    gemini_api_key: str = Field(default="your_key_here")
    default_model: str = Field(default="gemini-2.5-flash")
    premium_model: str = Field(default="gemini-2.5-pro")
    max_tokens: int = Field(default=1500)
    temperature: float = Field(default=0.3)

    # Telegram Interface
    telegram_bot_token: str = Field(default="")
    telegram_allowed_user_id: str = Field(default="")

    # Storage Paths
    chroma_db_path: str = Field(default="./data/chromadb")
    sqlite_db_path: str = Field(default="./data/shesheer_cmo.db")
    knowledge_base_path: str = Field(default="./data/knowledge_base")
    audio_cache_path: str = Field(default="./data/audio_cache")

    # Ingestion Controls
    max_concurrent_scrapers: int = Field(default=3)
    scrape_delay_seconds: int = Field(default=2)
    whisper_model: str = Field(default="base")

    # Feature Flags
    challenger_mode: bool = Field(default=True)
    memory_enabled: bool = Field(default=True)
    cost_tracking: bool = Field(default=True)
    debug_mode: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
