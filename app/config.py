from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://aud_look:aud_look@localhost:5432/aud_look"
    gemini_api_key: str | None = None
    vector_search_mode: str = "exact"
    model_device: str = "cpu"
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    audio_dir: Path = Path("dataset/audio")
    transcript_dir: Path = Path("dataset/transcripts")
    manifest_path: Path = Path("dataset/manifest.yaml")


@lru_cache
def get_settings() -> Settings:
    return Settings()
