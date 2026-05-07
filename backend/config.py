from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 5000
    is_dev: bool = False
    database_url: str = "sqlite:///./quiz_builder.db"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
