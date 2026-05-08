from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 5000
    is_dev: bool = False
    database_url: str = "sqlite:///./quiz_builder.db"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
