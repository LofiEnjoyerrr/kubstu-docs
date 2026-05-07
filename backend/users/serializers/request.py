from django.contrib.auth import authenticate
from rest_framework import serializers

from users.models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(
            username=data['username'],
            password=data['password']
        )

        if not user:
            raise serializers.ValidationError('Invalid credentials')

        data['user'] = user
        return data


class CredentialsAvailableSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(max_length=254)

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'password',
        )

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
