from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from app.db.db import create_db_and_tables
from app.routes import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # executed on startup
    create_db_and_tables()
    yield
    # executed on shutdown


app = FastAPI(lifespan=lifespan)

api_router = APIRouter()
api_router.include_router(users.router)
app.include_router(api_router, prefix="/api")
