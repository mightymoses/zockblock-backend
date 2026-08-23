import os
from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, create_engine
from testcontainers.community.postgres import PostgresContainer

from app.config import get_settings
from app.dependencies import get_session, require_auth
from app.main import app

# Works around a known Ryuk (testcontainers' cleanup sidecar) port-mapping
# issue on Windows/Docker Desktop. Containers we start ourselves via a
# context manager (see `engine` below) get cleaned up regardless.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Starts one real Postgres container for the whole test session,
    points app.config.Settings at it, and runs the Alembic migrations
    against it (instead of SQLModel.metadata.create_all()) — so the tests
    also verify that the migrations actually produce a working schema."""
    with PostgresContainer("postgres:18") as postgres:
        os.environ["POSTGRES_HOST"] = postgres.get_container_host_ip()
        os.environ["POSTGRES_PORT"] = str(postgres.get_exposed_port(5432))
        os.environ["POSTGRES_DB"] = postgres.dbname
        os.environ["POSTGRES_USER"] = postgres.username
        os.environ["POSTGRES_PASSWORD"] = postgres.password
        get_settings.cache_clear()

        command.upgrade(Config("alembic.ini"), "head")

        yield create_engine(get_settings().postgres_url)


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    """One DB session per test, wrapped in a transaction that's rolled back
    afterwards — so tests stay isolated from each other without needing a
    fresh container/schema for every single test. session.commit() calls in
    the code under test only close a savepoint, not the outer transaction."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    """A FastAPI TestClient for router/HTTP-level tests, with the DB session
    swapped for the test's own (see `session` above) and Auth0 authentication
    swapped for a fake, always-authenticated user — so tests don't need a
    real Postgres connection from the app itself or a real Auth0 token."""
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[require_auth] = lambda: {"sub": "auth0|test-user"}

    yield TestClient(app)

    app.dependency_overrides.clear()
