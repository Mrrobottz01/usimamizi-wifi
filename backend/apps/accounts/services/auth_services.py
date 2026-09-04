from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User


def authenticate_user(*, email: str, password: str) -> dict:
    """
    Authenticate user by email and password, returning JWT tokens and user payload.
    """
    user = authenticate(username=email, password=password)
    if not user:
        raise AuthenticationFailed('Invalid email or password.')

    if not user.is_active:
        raise AuthenticationFailed('User account is disabled.')

    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': user,
    }


def create_user_account(*, email: str, password: str = None, first_name: str = '', last_name: str = '', phone: str = '') -> User:
    """
    Create a new user account safely through service function.
    """
    return User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone=phone
    )
