import uuid
from datetime import datetime, timezone
from pydantic.alias_generators import to_camel
from sqlmodel import Field, SQLModel
from sqlmodel._compat import SQLModelConfig
from sqlalchemy import DateTime


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    model_config: SQLModelConfig = SQLModelConfig(
        alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    external_auth_id: str = Field(unique=True, index=True, min_length=6)
    username: str = Field(unique=True, index=True, max_length=255)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # pyright: ignore[reportArgumentType]
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # pyright: ignore[reportArgumentType]
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # pyright: ignore[reportArgumentType]
    )
