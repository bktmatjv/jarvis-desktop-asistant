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
    GROQ_API_KEYS: str
    MONGO_URI: str = "mongodb://localhost:27017"
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
