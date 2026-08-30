from fastapi import APIRouter
from app.dependencies import AuthDep, SessionDep
from app.users.application.command import user_command_service
from app.users.application.query import user_query_service
from app.users.schemas import (
    AvatarUploadRequest,
    AvatarUploadResponse,
    UserCreate,
    UserResponse,
    UsernameAvailabilityResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/current")
def get_current_user(auth: AuthDep, session: SessionDep) -> UserResponse:
    user = user_query_service.get_current_user(
        session, external_auth_id=str(auth.get("sub"))
    )
    return UserResponse.model_validate(user, from_attributes=True)


@router.get("/username-availability")
def check_username_availability(
    auth: AuthDep, session: SessionDep, username: str
) -> UsernameAvailabilityResponse:
    is_available = user_query_service.is_username_available(session, username)
    return UsernameAvailabilityResponse(is_available=is_available)


@router.post("/")
def create_user(auth: AuthDep, session: SessionDep, body: UserCreate) -> UserResponse:
    user = user_command_service.create_user(
        session, external_auth_id=str(auth.get("sub")), **body.model_dump()
    )
    return UserResponse.model_validate(user, from_attributes=True)


@router.patch("/current")
def update_current_user(
    auth: AuthDep, session: SessionDep, body: UserUpdate
) -> UserResponse:
    user = user_query_service.get_current_user(
        session, external_auth_id=str(auth.get("sub"))
    )
    updated_user = user_command_service.update_user(
        session, user=user, changes=body.model_dump(exclude_unset=True)
    )
    return UserResponse.model_validate(updated_user, from_attributes=True)


@router.post("/current/avatar-upload-url")
def create_avatar_upload_url(
    auth: AuthDep, body: AvatarUploadRequest
) -> AvatarUploadResponse:
    upload_url, avatar_url = user_command_service.request_avatar_upload_url(
        external_auth_id=str(auth.get("sub")), content_type=body.content_type
    )
    return AvatarUploadResponse(upload_url=upload_url, avatar_url=avatar_url)
