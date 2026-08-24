import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel
from sqlalchemy import DateTime


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
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
