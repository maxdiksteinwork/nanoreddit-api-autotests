from functools import lru_cache
from pydantic import ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    base_url: str = Field(default="http://localhost:8080")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str
    db_user: str
    db_password: SecretStr


    model_config = ConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
