from django.urls import path

from notifications.views import (
    SubscribeAPIView,
    UnsubscribeAPIView,
    VAPIDPublicKeyAPIView,
)

urlpatterns = [
    path('vapid-public-key/', VAPIDPublicKeyAPIView.as_view(), name='push-vapid-public-key'),
    path('subscribe/', SubscribeAPIView.as_view(), name='push-subscribe'),
    path('unsubscribe/', UnsubscribeAPIView.as_view(), name='push-unsubscribe'),
]
