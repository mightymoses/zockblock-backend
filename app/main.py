from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from app.logging import configure_logging
from app.users.exceptions import UserNotFoundException
from app.users.router import router as users_router

configure_logging()

app = FastAPI()


@app.exception_handler(UserNotFoundException)
def handle_user_not_found(request: Request, exc: UserNotFoundException) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "User not found"})


api_router = APIRouter()
api_router.include_router(users_router)
app.include_router(api_router, prefix="/api")
