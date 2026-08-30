import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# alphanumeric "words" separated by single ./_/- characters, e.g. "a.b-c" -
# first/last char is always alphanumeric, two special characters can never
# be adjacent (e.g. "a..b"). Length is constrained separately via min/max_length,
# since pydantic-core's regex engine (Rust, not Python's re) doesn't support
# lookahead/lookbehind.
USERNAME_PATTERN = r"^[a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*$"

ALLOWED_AVATAR_CONTENT_TYPES = Literal["image/jpeg", "image/png", "image/webp"]


class UserCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    animal_asset_name: str | None = None
    avatar_color: int | None = None
    bio_line_1: str | None = Field(default=None, max_length=100)
    bio_line_2: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = None


class UserUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    username: str | None = Field(default=None, min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    animal_asset_name: str | None = None
    avatar_color: int | None = None
    bio_line_1: str | None = Field(default=None, max_length=100)
    bio_line_2: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    username: str
    animal_asset_name: str | None
    avatar_color: int | None
    bio_line_1: str | None
    bio_line_2: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


class AvatarUploadRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    content_type: ALLOWED_AVATAR_CONTENT_TYPES


class AvatarUploadResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    upload_url: str
    avatar_url: str


class UsernameAvailabilityResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    is_available: bool
