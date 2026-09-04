from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.auth_services import authenticate_user
from .serializers import LoginSerializer, UserSerializer


class LoginView(APIView):
    """
    POST /api/v1/accounts/auth/login/
    Authenticate user and return access/refresh tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        auth_data = authenticate_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )

        user_serializer = UserSerializer(auth_data['user'])
        return Response({
            'access': auth_data['access'],
            'refresh': auth_data['refresh'],
            'user': user_serializer.data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/accounts/auth/logout/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Client discards JWT token on logout
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    GET /api/v1/accounts/auth/me/
    Get authenticated user profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
