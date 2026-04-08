from django.contrib.auth import login, logout
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from users.serializers.request import LoginSerializer, RegisterSerializer
from users.serializers.response import UserSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer(),
        responses={
            200: OpenApiResponse(
                description="Успешный вход",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "user": {"type": "string"},
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        login(request, user)

        return Response({
            'message': 'Logged in',
            'user': user.username
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LoginSerializer(),
        responses={
            200: OpenApiResponse(
                description="Успешный вход",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                    }
                }
            )
        }
    )
    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out'})


class RegisterView(APIView):
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
