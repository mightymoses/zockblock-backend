from sqlmodel import create_engine
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.postgres_url)
