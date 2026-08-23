from sqlmodel import Session
from app.users import repository
from app.users.exceptions import UserNotFoundException
from app.users.models import User


def get_current_user(session: Session, external_auth_id: str) -> User:
    user = repository.get_by_external_auth_id(session, external_auth_id)

    if not user:
        raise UserNotFoundException()

    return user
