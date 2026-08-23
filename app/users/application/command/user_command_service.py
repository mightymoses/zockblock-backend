from sqlmodel import Session
from app.users import repository
from app.users.models import User


def create_user(session: Session, username: str, external_auth_id: str) -> User:
    user = User(username=username, external_auth_id=external_auth_id)
    repository.add(session, user)

    session.commit()
    session.refresh(user)

    return user
