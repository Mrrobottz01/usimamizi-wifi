from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Standardized API error handler.
    Ensures all error responses follow the standard format:
    {
      "code": "ERROR_CODE",
      "detail": "Human-readable error description.",
      "field_errors": {}
    }
    """
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled server exceptions
        return Response(
            {
                "code": "INTERNAL_SERVER_ERROR",
                "detail": "An unexpected server error occurred.",
                "field_errors": {}
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    code = "API_ERROR"
    field_errors = {}
    detail = "An error occurred."

    if isinstance(exc, ValidationError):
        code = "VALIDATION_ERROR"
        detail = "The request contains invalid data."
        if isinstance(response.data, dict):
            field_errors = response.data
        elif isinstance(response.data, list):
            field_errors = {"non_field_errors": response.data}
    elif isinstance(exc, NotAuthenticated):
        code = "UNAUTHENTICATED"
        detail = "Authentication credentials were not provided."
    elif isinstance(exc, AuthenticationFailed):
        code = "AUTHENTICATION_FAILED"
        detail = str(exc.detail) if hasattr(exc, 'detail') else "Invalid authentication credentials."
    elif isinstance(exc, PermissionDenied):
        code = "PERMISSION_DENIED"
        detail = str(exc.detail) if hasattr(exc, 'detail') else "You do not have permission to perform this action."
    elif isinstance(exc, NotFound):
        code = "NOT_FOUND"
        detail = str(exc.detail) if hasattr(exc, 'detail') else "The requested resource was not found."
    elif isinstance(exc, APIException):
        code = getattr(exc, 'default_code', 'API_ERROR').upper()
        detail = str(exc.detail) if hasattr(exc, 'detail') else str(exc)

    response.data = {
        "code": code,
        "detail": detail,
        "field_errors": field_errors
    }

    return response
