from functools import lru_cache
from typing import Literal
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["local", "production"] = "local"

    auth0_domain: str = ""
    auth0_api_audience: str = ""

    # set directly by most hosting platforms (e.g. Render's `fromDatabase`
    # only exposes a full connection string, not separate host/port). Takes
    # precedence over the individual postgres_* fields below when set.
    database_url: str = ""

    postgres_host: str = ""
    postgres_port: str = ""
    postgres_db: str = ""
    postgres_user: str = ""
    postgres_password: str = ""

    r2_endpoint_url: str = ""
    r2_bucket_name: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_public_base_url: str = ""
    presigned_url_expiry_seconds: int = 300

    @computed_field
    @property
    def postgres_url(self) -> str:
        if self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return Settings()
