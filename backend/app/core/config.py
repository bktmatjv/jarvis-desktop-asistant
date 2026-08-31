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
    TAVILY_API_KEY: str = ""

    # Dual-Model Architecture (Groq Cloud Only)
    # Fast router model: classifies intent, generates stalling phrases
    ROUTER_MODEL: str = "openai/gpt-oss-20b"
    # Heavy reasoning model: handles tool calling and complex reasoning
    REASONING_MODEL: str = "qwen/qwen3.6-27b"
    # Enable stalling phrases while reasoning model works
    STALLING_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
