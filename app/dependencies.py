from collections.abc import Generator
from typing import Annotated, Any
from app.config import get_settings
from app.db.db import engine
from fastapi import Depends
from fastapi_plugin import Auth0FastAPI
from sqlmodel import Session

settings = get_settings()

auth0 = Auth0FastAPI(domain=settings.auth0_domain, audience=settings.auth0_api_audience)

# named separately (instead of inline in AuthDep) so tests can override this
# exact callable via app.dependency_overrides
require_auth = auth0.require_auth()
AuthDep = Annotated[dict[Any, Any], Depends(require_auth)]


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
