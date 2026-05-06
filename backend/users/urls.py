from django.urls import path
from .views import LoginAPIView, LogoutAPIView, RegisterAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='user_login'),
    path('logout/', LogoutAPIView.as_view(), name='user_logout'),
    path('register/', RegisterAPIView.as_view(), name='user_register'),
]
