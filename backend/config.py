from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_multimodal_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    nvidia_embedding_dims: int = 1024

    brave_search_api_key: str = ""

    mongodb_uri: str = "mongodb://localhost:27017"
    db_name: str = "chatbot"

    redis_url: str = ""

    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    auth_secret_key: str = "dev-only-change-before-production-9f3a7c1e6b4d8a2f5c0e7b1d9a6f3c8e"
    auth_cookie_secure: bool = False
    auth_session_hours: int = 24

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
