from sqlmodel import Session, select
from app.users.models import User


def get_by_external_auth_id(session: Session, external_auth_id: str) -> User | None:
    statement = select(User).where(User.external_auth_id == external_auth_id)
    return session.exec(statement).first()


def add(session: Session, user: User) -> User:
    session.add(user)
    session.flush()
    return user


def exists_by_username(session: Session, username: str) -> bool:
    statement = select(User.id).where(User.username == username)
    return session.exec(statement).first() is not None
