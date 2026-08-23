from fastapi import APIRouter, FastAPI
from app.routes import users

app = FastAPI()

api_router = APIRouter()
api_router.include_router(users.router)
app.include_router(api_router, prefix="/api")
