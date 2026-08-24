from fastapi import APIRouter
from app.dependencies import AuthDep, SessionDep
from app.users.application.command import user_command_service
from app.users.application.query import user_query_service
from app.users.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/current")
def get_current_user(auth: AuthDep, session: SessionDep) -> UserResponse:
    user = user_query_service.get_current_user(
        session, external_auth_id=str(auth.get("sub"))
    )
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/")
def create_user(auth: AuthDep, session: SessionDep, body: UserCreate) -> UserResponse:
    user = user_command_service.create_user(
        session, username=body.username, external_auth_id=str(auth.get("sub"))
    )
    return UserResponse.model_validate(user, from_attributes=True)
