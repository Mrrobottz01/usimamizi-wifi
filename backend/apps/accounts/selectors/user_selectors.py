from typing import Optional

from ..models import User


def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Get a single user by ID.
    """
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def get_user_by_email(email: str) -> Optional[User]:
    """
    Get a single user by email.
    """
    try:
        return User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return None
