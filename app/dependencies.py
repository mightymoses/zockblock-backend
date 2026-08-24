from collections.abc import Generator
from functools import lru_cache
from typing import Annotated, Any
from app.config import get_settings
from app.db.db import get_engine
from fastapi import Depends, Request
from fastapi_plugin import Auth0FastAPI
from sqlmodel import Session


@lru_cache
def get_auth0_client() -> Auth0FastAPI:
    settings = get_settings()
    return Auth0FastAPI(domain=settings.auth0_domain, audience=settings.auth0_api_audience)


# a plain, importable function (instead of the closure auth0.require_auth()
# returns) so tests can override this exact callable via
# app.dependency_overrides, while still only constructing the Auth0 client
# lazily on first real request instead of at import time
async def require_auth(request: Request) -> dict[Any, Any]:
    return await get_auth0_client().require_auth()(request)


AuthDep = Annotated[dict[Any, Any], Depends(require_auth)]


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
