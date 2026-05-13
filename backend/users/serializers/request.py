from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from users.constants import MAX_REGISTRATION_ATTEMPTS_PER_WEEK, EMAIL_VERIFY_TOKEN_LENGTH, EMAIL_VERIFY_REQUEST_LIFETIME
from users.models import User, RegisterRequest
from users.utils import generate_username, generate_email_verify_token


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

