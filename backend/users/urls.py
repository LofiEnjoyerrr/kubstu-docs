from django.urls import path
from .views import LoginView, LogoutView, MeView, RegisterView, FindUserView

urlpatterns = [
    path('login/', LoginView.as_view(), name='user_login'),
    path('logout/', LogoutView.as_view(), name='user_logout'),
    path('me/', MeView.as_view(), name='user_me'),
    path('register/', RegisterView.as_view(), name='user_register'),
    path('find_user/', FindUserView.as_view(), name='find_user'),
]
