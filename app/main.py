from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from app.logging import configure_logging
from app.terms.exceptions import TermsNotConfiguredException
from app.terms.router import router as terms_router
from app.users.exceptions import (
    InvalidAvatarModeException,
    InvalidAvatarUrlException,
    OutdatedTermsVersionException,
    UserNotFoundException,
    UsernameAlreadyTakenException,
)
from app.users.router import router as users_router

configure_logging()

app = FastAPI()


@app.exception_handler(UserNotFoundException)
def handle_user_not_found(request: Request, exc: UserNotFoundException) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "User not found"})


@app.exception_handler(UsernameAlreadyTakenException)
def handle_username_already_taken(
    request: Request, exc: UsernameAlreadyTakenException
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": "Username already taken"})


@app.exception_handler(InvalidAvatarUrlException)
def handle_invalid_avatar_url(
    request: Request, exc: InvalidAvatarUrlException
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": "Invalid avatar URL"})


@app.exception_handler(InvalidAvatarModeException)
def handle_invalid_avatar_mode(
    request: Request, exc: InvalidAvatarModeException
) -> JSONResponse:
    return JSONResponse(
        status_code=400, content={"detail": "avatar_mode 'photo' requires an avatar_url"}
    )


@app.exception_handler(OutdatedTermsVersionException)
def handle_outdated_terms_version(
    request: Request, exc: OutdatedTermsVersionException
) -> JSONResponse:
    return JSONResponse(
        status_code=400, content={"detail": "Only the current terms version can be accepted"}
    )


@app.exception_handler(TermsNotConfiguredException)
def handle_terms_not_configured(
    request: Request, exc: TermsNotConfiguredException
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Terms of use are not configured"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(terms_router)
app.include_router(api_router, prefix="/api")
