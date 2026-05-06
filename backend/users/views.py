from django.contrib.auth import login, logout
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from users.serializers.request import LoginSerializer, RegisterSerializer
from users.serializers.response import UserSerializer
from users.throttling import LoginRateThrottle


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    throttle_scope = 'users_login_scope'

    @extend_schema(
        request=LoginSerializer(),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Успешный вход',
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description='Неверные данные',
            ),
            status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
                description='Слишком много запросов',
            ),
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        login(request, user)

        return Response(status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LoginSerializer(),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Успешный выход',
            ),
        }
    )
    def post(self, request):
        logout(request)

        return Response(status=status.HTTP_200_OK)


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer(),
        responses=UserSerializer(),
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created_user = serializer.save()

        return Response(data=UserSerializer(created_user).data, status=status.HTTP_201_CREATED)
