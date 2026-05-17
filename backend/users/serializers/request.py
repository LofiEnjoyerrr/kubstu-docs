from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from users.constants import (
    MAX_REGISTRATION_ATTEMPTS_PER_WEEK,
    EMAIL_VERIFY_TOKEN_LENGTH,
    EMAIL_VERIFY_REQUEST_LIFETIME,
    PASSWORD_RESET_TOKEN_LENGTH,
    PASSWORD_RESET_REQUEST_LIFETIME,
)
from users.models import User, RegisterRequest, PasswordResetRequest
from users.utils import generate_username, generate_email_verify_token, generate_password_reset_token


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(
            username=data['username'],
            password=data['password']
        )

        if not user:
            raise serializers.ValidationError('Неверные учётные данны')

        data['user'] = user
        return data


class CredentialsAvailableSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):

    ip = serializers.IPAddressField()

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'password',
            'ip',
        )
        extra_kwargs = {
            'username': {'required': False, 'default': '', 'allow_blank': True},
        }

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        ip = attrs.get('ip')

        if not username:
            username = generate_username(email)
        attrs['username'] = username

        one_week_ago = (datetime.now() - timedelta(weeks=1)).date()
        if RegisterRequest.objects.filter(
            email=email,
            ip=ip,
            dt_created__date__gte=one_week_ago,
        ).count() >= MAX_REGISTRATION_ATTEMPTS_PER_WEEK:
            raise ValidationError('Превышено число попыток регистрации за неделю')

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        password = make_password(password)

        token = generate_email_verify_token()

        register_request = RegisterRequest(**validated_data, password=password, token=token)
        register_request.save()
        register_request.send_email_verify()

        return register_request


class EmailVerifySerializer(serializers.Serializer):
    register_request: RegisterRequest

    token = serializers.CharField(min_length=EMAIL_VERIFY_TOKEN_LENGTH, max_length=EMAIL_VERIFY_TOKEN_LENGTH)

    def validate_token(self, value: str):
        request_lifetime = datetime.now() - timedelta(minutes=EMAIL_VERIFY_REQUEST_LIFETIME)

        register_request = RegisterRequest.objects.filter(
            dt_created__gte=request_lifetime,
            status=RegisterRequest.RegisterRequestStatus.WAIT,
        ).first()
        if not register_request:
            raise ValidationError('Нет подходящего запроса на подтверждение электронной почты')

        self.register_request = register_request
        return value

    def create(self, validated_data):
        new_user = User(
            email=self.register_request.email,
            username=self.register_request.username,
            password=self.register_request.password,
        )
        new_user.save()

        self.register_request.status = RegisterRequest.RegisterRequestStatus.COMPLETE
        self.register_request.save()

        return new_user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'avatar')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'username': {'required': False},
            'avatar': {'required': False},
        }

    def validate_username(self, value: str):
        if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Имя пользователя уже занято')
        return value


class UserSearchSerializer(serializers.Serializer):
    q = serializers.CharField(min_length=1, max_length=150)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            # Return without error to not leak whether an email is registered.
            return value

        self.user = user
        return value

    def create(self, validated_data):
        if not hasattr(self, 'user'):
            return None

        token = generate_password_reset_token()
        reset_request = PasswordResetRequest(user=self.user, token=token)
        reset_request.save()
        reset_request.send_password_reset()

        return reset_request


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(
        min_length=PASSWORD_RESET_TOKEN_LENGTH,
        max_length=PASSWORD_RESET_TOKEN_LENGTH,
    )
    password = serializers.CharField(min_length=8)

    def validate_token(self, value: str):
        threshold = datetime.now() - timedelta(minutes=PASSWORD_RESET_REQUEST_LIFETIME)

        reset_request = PasswordResetRequest.objects.filter(
            token=value,
            status=PasswordResetRequest.PasswordResetRequestStatus.WAIT,
            dt_created__gte=threshold,
        ).first()

        if not reset_request:
            raise ValidationError('Нет действующего запроса на сброс пароля с таким токеном')

        self.reset_request = reset_request
        return value

    def save(self, **kwargs):
        user = self.reset_request.user
        user.set_password(self.validated_data['password'])
        user.save()

        self.reset_request.status = PasswordResetRequest.PasswordResetRequestStatus.COMPLETE
        self.reset_request.save()

        # Invalidate all other pending reset requests for this user.
        PasswordResetRequest.objects.filter(
            user=user,
            status=PasswordResetRequest.PasswordResetRequestStatus.WAIT,
        ).update(status=PasswordResetRequest.PasswordResetRequestStatus.EXPIRED)

        return user

