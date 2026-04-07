from django.contrib.auth import login, logout
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from users.selectors import get_user_by_username
from users.serializers import LoginSerializer, RegisterSerializer, UserSerializer, FindUserSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

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

    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'username': request.user.username
        })


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_user = serializer.save()
        return Response(data=UserSerializer(created_user).data, status=status.HTTP_201_CREATED)


class FindUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FindUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_by_username(serializer.validated_data['username'])
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data=UserSerializer(user).data, status=status.HTTP_200_OK)
