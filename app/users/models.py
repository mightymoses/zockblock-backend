import uuid
from datetime import datetime, timezone
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import DateTime, UniqueConstraint
from app.config import get_settings


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    external_auth_id: str | None = Field(default=None, unique=True, index=True, min_length=6)
    username: str = Field(unique=True, index=True, max_length=255)
    avatar_url: str | None = Field(default=None)
    avatar_mode: str = Field(default="animal")
    animal_asset_name: str | None = Field(default=None, max_length=100)
    avatar_color: int | None = Field(default=None)
    bio: str | None = Field(default=None, max_length=150)
    # None = never asked (only possible for users created before consents were introduced)
    crash_reports_consent: bool | None = Field(default=None)
    crash_reports_consent_updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # pyright: ignore[reportArgumentType]
    )
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
    # selectin: always loaded together with the user, so the response needs no extra query
    terms_acceptances: list["TermsAcceptance"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    @property
    def latest_terms_acceptance(self) -> "TermsAcceptance | None":
        return max(self.terms_acceptances, key=lambda acceptance: acceptance.accepted_at, default=None)

    @property
    def accepted_terms_version(self) -> str | None:
        latest = self.latest_terms_acceptance
        return latest.terms_version if latest else None

    @property
    def accepted_terms_at(self) -> datetime | None:
        latest = self.latest_terms_acceptance
        return latest.accepted_at if latest else None

    @property
    def has_accepted_current_terms(self) -> bool:
        return self.has_accepted_terms(get_settings().current_terms_version)

    def has_accepted_terms(self, terms_version: str) -> bool:
        return any(acceptance.terms_version == terms_version for acceptance in self.terms_acceptances)


class TermsAcceptance(SQLModel, table=True):
    """One row per terms version a user agreed to - kept as proof, never updated or deleted."""

    __tablename__ = "terms_acceptance"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("user_id", "terms_version", name="uq_terms_acceptance_user_id_terms_version"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    terms_version: str = Field(max_length=10)
    accepted_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # pyright: ignore[reportArgumentType]
    )
