from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from docs.models import Document
from notifications.models import (
    DocumentNotificationSettings,
    PushSubscription,
    UserNotificationSettings,
)
from notifications.serializers import (
    DocumentNotificationSettingsSerializer,
    PushSubscriptionSerializer,
    PushUnsubscribeSerializer,
    UserNotificationSettingsSerializer,
)


class VAPIDPublicKeyAPIView(APIView):
    """
    Returns the server's VAPID public key in URL-safe base64. The frontend
    needs it to build a ``PushSubscription`` via the browser's PushManager —
    it identifies who's allowed to send notifications to this endpoint.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            status.HTTP_200_OK: OpenApiResponse(description='Публичный VAPID-ключ'),
        },
    )
    def get(self, request):
        key = getattr(settings, 'VAPID_PUBLIC_KEY', '') or ''
        return Response({'public_key': key})


class SubscribeAPIView(APIView):
    """Register (or refresh) a Web Push subscription for the current user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PushSubscriptionSerializer,
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(description='Подписка сохранена'),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description='Некорректные данные'),
        },
    )
    def post(self, request):
        serializer = PushSubscriptionSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)


class UnsubscribeAPIView(APIView):
    """Remove a Web Push subscription (called when the user disables pushes)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PushUnsubscribeSerializer,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Подписка удалена'),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description='Некорректные данные'),
        },
    )
    def post(self, request):
        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushSubscription.objects.filter(
            user=request.user,
            endpoint=serializer.validated_data['endpoint'],
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserNotificationSettingsAPIView(APIView):
    """Read/update owner-wide notification preferences."""

    permission_classes = [IsAuthenticated]

    def _get_settings(self, user) -> UserNotificationSettings:
        settings_obj, _ = UserNotificationSettings.objects.get_or_create(user=user)
        return settings_obj

    @extend_schema(responses=UserNotificationSettingsSerializer)
    def get(self, request):
        serializer = UserNotificationSettingsSerializer(self._get_settings(request.user))
        return Response(serializer.data)

    @extend_schema(request=UserNotificationSettingsSerializer, responses=UserNotificationSettingsSerializer)
    def patch(self, request):
        settings_obj = self._get_settings(request.user)
        serializer = UserNotificationSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DocumentNotificationSettingsAPIView(APIView):
    """Read/update notification preferences for one owned document."""

    permission_classes = [IsAuthenticated]

    def _get_document(self, request, doc_id: int) -> Document:
        return Document.objects.get(pk=doc_id, owner=request.user)

    def _get_settings(self, document: Document) -> DocumentNotificationSettings:
        settings_obj, _ = DocumentNotificationSettings.objects.get_or_create(document=document)
        return settings_obj

    @extend_schema(responses=DocumentNotificationSettingsSerializer)
    def get(self, request, doc_id: int):
        try:
            document = self._get_document(request, doc_id)
        except Document.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = DocumentNotificationSettingsSerializer(self._get_settings(document))
        return Response(serializer.data)

    @extend_schema(request=DocumentNotificationSettingsSerializer, responses=DocumentNotificationSettingsSerializer)
    def patch(self, request, doc_id: int):
        try:
            document = self._get_document(request, doc_id)
        except Document.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        settings_obj = self._get_settings(document)
        serializer = DocumentNotificationSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
