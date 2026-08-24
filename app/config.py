from functools import lru_cache
from typing import Literal
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["local", "production"] = "local"

    auth0_domain: str = ""
    auth0_api_audience: str = ""

    postgres_host: str = ""
    postgres_port: str = ""
    postgres_db: str = ""
    postgres_user: str = ""
    postgres_password: str = ""

    @computed_field
    @property
    def postgres_url(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return Settings()
