from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "thinkingmachines/inkling"

    mongodb_uri: str = "mongodb://localhost:27017"
    db_name: str = "chatbot"

    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
