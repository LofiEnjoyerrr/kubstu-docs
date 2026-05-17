from django.contrib.auth import login, logout
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from common_utils.ip import get_client_ip
from users.constants import (
    EMAIL_VERIFY_REQUEST_MESSAGE,
    EMAIL_VERIFY_REQUEST_LIFETIME,
    PASSWORD_RESET_REQUEST_MESSAGE,
    PASSWORD_RESET_REQUEST_LIFETIME,
)
from users.models import User
from users.serializers.request import (
    LoginSerializer,
    RegisterSerializer,
    EmailVerifySerializer,
    UserSearchSerializer,
    UserUpdateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from users.serializers.response import UserSerializer
from users.services import validate_credentials
from users.throttling import ExtendedRateThrottle


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ExtendedRateThrottle]
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


class CredentialAvailableAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description='Учётные данные доступны',
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description='Учётные данные не доступны',
            ),
        }
    )
    def get(self, request, credential_type, credential):
        credential_is_valid = validate_credentials(credential_type, credential)
        if not credential_is_valid:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_200_OK)


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ExtendedRateThrottle]
    throttle_scope = 'users_register_scope'

    @extend_schema(
        request=RegisterSerializer,
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                response=OpenApiTypes.STR,
                description='Письмо для подтверждения электронной почты отправлено',
                examples=[
                    OpenApiExample(
                        'Success',
                        value=EMAIL_VERIFY_REQUEST_MESSAGE.format(
                            EMAIL_VERIFY_REQUEST_LIFETIME
                        ),
                    )
                ],
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description='Учётные данные не валидны',
            ),
        },
    )
    def post(self, request):
        user_ip = get_client_ip(request)
        serializer = RegisterSerializer(data=request.data | {'ip': user_ip})
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            data=EMAIL_VERIFY_REQUEST_MESSAGE.format(EMAIL_VERIFY_REQUEST_LIFETIME),
            status=status.HTTP_201_CREATED,
        )


class EmailVerifyAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ExtendedRateThrottle]
    throttle_scope = 'users_email_verify'

    @extend_schema(
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                response=OpenApiTypes.STR,
                description='Электронная почта успешно подтверждена',
                examples=[
                    OpenApiExample(
                        'Success',
                        value=EMAIL_VERIFY_REQUEST_MESSAGE.format(
                            EMAIL_VERIFY_REQUEST_LIFETIME
                        ),
                    )
                ],
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description='Учётные данные не валидны',
            ),
        },
    )
    def get(self, request, token):
        serializer = EmailVerifySerializer(data={'token': token})
        serializer.is_valid(raise_exception=True)

        new_user = serializer.save()
        login(request, new_user)

        return Response(
            data='Электронная почта успешно подтверждена',
            status=status.HTTP_200_OK,
        )


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer())
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(request=UserUpdateSerializer(), responses=UserSerializer())
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class UserSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[UserSearchSerializer],
        responses={
            status.HTTP_200_OK: UserSerializer(many=True),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description='Некорректный запрос'),
        },
    )
    def get(self, request):
        serializer = UserSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['q']
        users = User.objects.filter(username__icontains=query).exclude(pk=request.user.pk)[:20]

        return Response(data=UserSerializer(users, many=True).data, status=status.HTTP_200_OK)


class PasswordResetAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ExtendedRateThrottle]
    throttle_scope = 'users_password_reset_scope'

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=OpenApiTypes.STR,
                description='Письмо для сброса пароля отправлено (или адрес не найден — ответ одинаков)',
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description='Некорректный запрос'),
        },
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=PASSWORD_RESET_REQUEST_MESSAGE.format(PASSWORD_RESET_REQUEST_LIFETIME),
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ExtendedRateThrottle]
    throttle_scope = 'users_password_reset_scope'

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(description='Пароль успешно изменён'),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description='Токен недействителен или истёк'),
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data='Пароль успешно изменён', status=status.HTTP_200_OK)
