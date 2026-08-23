from sqlmodel import Session
from app.users.application.command import user_command_service
from app.users.application.query import user_query_service


def test_created_user_can_be_fetched_again(session: Session):
    created = user_command_service.create_user(
        session, username="alice", external_auth_id="auth0|123"
    )

    fetched = user_query_service.get_current_user(
        session, external_auth_id="auth0|123"
    )

    assert fetched.id == created.id
    assert fetched.username == "alice"
