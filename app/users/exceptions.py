class UserNotFoundException(Exception):
    """Raised when no user exists for the given external auth id."""


class UsernameAlreadyTakenException(Exception):
    """Raised when the given username is already taken by another user."""


class InvalidAvatarUrlException(Exception):
    """Raised when an avatar_url is set that wasn't produced by our own upload flow."""
