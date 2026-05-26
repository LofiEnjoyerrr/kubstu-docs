from django.urls import path

from .views import (
    LoginAPIView,
    LogoutAPIView,
    RegisterAPIView,
    CredentialAvailableAPIView,
    EmailVerifyAPIView,
    FavoriteUserDetailAPIView,
    FavoriteUsersAPIView,
    MeAPIView,
    UserSearchAPIView,
    PasswordResetAPIView,
    PasswordResetConfirmAPIView,
)

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
    path('email/verify/<str:token>/', EmailVerifyAPIView.as_view(), name='users_email_verify'),
    path('me/', MeAPIView.as_view(), name='users_me'),
    path('search/', UserSearchAPIView.as_view(), name='users_search'),
    path('favorites/', FavoriteUsersAPIView.as_view(), name='users_favorites'),
    path('favorites/<int:user_id>/', FavoriteUserDetailAPIView.as_view(), name='users_favorite_detail'),
    path('password-reset/', PasswordResetAPIView.as_view(), name='users_password_reset'),
    path('password-reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='users_password_reset_confirm'),
]
