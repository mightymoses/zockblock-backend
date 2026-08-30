import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel
from sqlalchemy import DateTime


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    external_auth_id: str | None = Field(default=None, unique=True, index=True, min_length=6)
    username: str = Field(unique=True, index=True, max_length=255)
    avatar_url: str | None = Field(default=None)
    animal_asset_name: str | None = Field(default=None, max_length=100)
    avatar_color: int | None = Field(default=None)
    bio_line_1: str | None = Field(default=None, max_length=100)
    bio_line_2: str | None = Field(default=None, max_length=100)
    owner_user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)
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
