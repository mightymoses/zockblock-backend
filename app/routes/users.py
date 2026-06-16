from sqlmodel import select
from fastapi import APIRouter, HTTPException
from app.models.users import User
from app.dependencies import AuthDep, SessionDep

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/current")
def get_current_user(auth: AuthDep, session: SessionDep) -> User:
    statement = select(User).where(User.external_auth_id == str(auth.get("sub")))
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/")
def create_user(auth: AuthDep, session: SessionDep, user: User) -> User:
    user.external_auth_id = str(auth.get("sub"))
    session.add(user)
    session.commit()
    session.refresh(user)

    return user
