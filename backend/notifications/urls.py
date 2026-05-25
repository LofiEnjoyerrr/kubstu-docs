from django.urls import path

from notifications.views import (
    DocumentNotificationSettingsAPIView,
    SubscribeAPIView,
    UnsubscribeAPIView,
    UserNotificationSettingsAPIView,
    VAPIDPublicKeyAPIView,
)

urlpatterns = [
    path('vapid-public-key/', VAPIDPublicKeyAPIView.as_view(), name='push-vapid-public-key'),
    path('subscribe/', SubscribeAPIView.as_view(), name='push-subscribe'),
    path('unsubscribe/', UnsubscribeAPIView.as_view(), name='push-unsubscribe'),
    path('preferences/', UserNotificationSettingsAPIView.as_view(), name='notification-preferences'),
    path(
        'documents/<int:doc_id>/preferences/',
        DocumentNotificationSettingsAPIView.as_view(),
        name='document-notification-preferences',
    ),
]
