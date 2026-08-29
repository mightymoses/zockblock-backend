from functools import lru_cache
from sqlalchemy import Engine
from sqlmodel import create_engine
from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().postgres_url)
