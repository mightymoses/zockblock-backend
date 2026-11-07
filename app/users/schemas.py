import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

# alphanumeric "words" separated by single ./_/- characters, e.g. "a.b-c" -
# first/last char is always alphanumeric, two special characters can never
# be adjacent (e.g. "a..b"). Length is constrained separately via min/max_length,
# since pydantic-core's regex engine (Rust, not Python's re) doesn't support
# lookahead/lookbehind.
USERNAME_PATTERN = r"^[a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*$"

ALLOWED_AVATAR_CONTENT_TYPES = Literal["image/jpeg", "image/png", "image/webp"]

AVATAR_MODES = Literal["animal", "photo"]

# avatar colors are ARGB values as sent by the app (e.g. 0xFF52A788) - 32 bit, unsigned
MAX_ARGB_COLOR = 0xFFFFFFFF

# terms versions are dates, e.g. "2026-11-01"
TERMS_VERSION_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class UserCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    animal_asset_name: str = Field(min_length=1, max_length=100)
    avatar_color: int = Field(ge=0, le=MAX_ARGB_COLOR)
    bio: str | None = Field(default=None, max_length=150)
    avatar_url: str | None = None
    avatar_mode: AVATAR_MODES = "animal"
    crash_reports_consent: bool
    accepted_terms_version: str = Field(pattern=TERMS_VERSION_PATTERN)


class UserUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    username: str | None = Field(default=None, min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    animal_asset_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_color: int | None = Field(default=None, ge=0, le=MAX_ARGB_COLOR)
    bio: str | None = Field(default=None, max_length=150)
    avatar_url: str | None = None
    avatar_mode: AVATAR_MODES | None = None
    crash_reports_consent: bool | None = None
    accepted_terms_version: str | None = Field(default=None, pattern=TERMS_VERSION_PATTERN)

    @field_validator("animal_asset_name", "avatar_color", "crash_reports_consent", "accepted_terms_version")
    @classmethod
    def reject_explicit_null(cls, value: bool | int | str | None) -> bool | int | str | None:
        # only runs for fields actually sent - omitting them is fine, resetting them to null isn't
        if value is None:
            raise ValueError("may be omitted, but not set to null")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    username: str
    animal_asset_name: str | None
    avatar_color: int | None
    bio: str | None
    avatar_url: str | None
    avatar_mode: AVATAR_MODES
    crash_reports_consent: bool | None
    crash_reports_consent_updated_at: datetime | None
    accepted_terms_version: str | None
    accepted_terms_at: datetime | None
    has_accepted_current_terms: bool
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
