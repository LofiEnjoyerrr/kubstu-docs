from django.urls import path
from .views import LoginAPIView, LogoutAPIView, RegisterAPIView, CredentialAvailableAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='users_login'),
    path('logout/', LogoutAPIView.as_view(), name='users_logout'),
    path('register/', RegisterAPIView.as_view(), name='users_register'),
    path(
        'credentials/username/<str:credential>/available/',
        CredentialAvailableAPIView.as_view(),
        kwargs={'credential_type': 'username'},
        name='users_credential_username_available',
    ),
    path(
        'credentials/email/<str:credential>/available/',
        CredentialAvailableAPIView.as_view(),
        kwargs={'credential_type': 'email'},
        name='users_credential_email_available',
    ),
]
