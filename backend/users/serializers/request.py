from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from users.constants import MAX_REGISTRATION_ATTEMPTS_PER_WEEK
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