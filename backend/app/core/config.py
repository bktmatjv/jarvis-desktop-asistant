"""
Configuration module.
Loads environment variables from the root .env file and defines the Settings schema.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent.parent
env_path = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # Segregated Groq API Keys (with fallback to GROQ_API_KEYS if empty)
    GROQ_API_KEYS: str = ""
    GROQ_API_KEYS_FAST: str = ""
    GROQ_API_KEYS_REASONING: str = ""
    GROQ_API_KEYS_VOICE: str = ""

    MONGO_URI: str = "mongodb://localhost:27017"
    TAVILY_API_KEY: str = ""

    # Model Architecture
    ROUTER_MODEL: str = "groq/compound-mini"
    FAST_MODEL: str = "groq/compound-mini"
    REASONING_MODEL: str = "qwen/qwen3.6-27b"
    VOICE_MODEL: str = "whisper-large-v3-turbo"

    STALLING_ENABLED: bool = True

    # User Profile
    USER_NAME: str = "MATIAS JAVIER"
    USER_ROLE: str = "admin"

    def get_fast_keys(self) -> list[str]:
        keys = self.GROQ_API_KEYS_FAST or self.GROQ_API_KEYS
        return [k.strip() for k in keys.split(",") if k.strip()]

    def get_reasoning_keys(self) -> list[str]:
        keys = self.GROQ_API_KEYS_REASONING or self.GROQ_API_KEYS
        return [k.strip() for k in keys.split(",") if k.strip()]

    def get_voice_keys(self) -> list[str]:
        keys = self.GROQ_API_KEYS_VOICE or self.GROQ_API_KEYS
        return [k.strip() for k in keys.split(",") if k.strip()]

    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

