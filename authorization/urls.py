from django.urls import path

from .views import SignupAPIView, LoginAPIView, LogoutAPIView, CookieTokenRefreshView

urlpatterns = [
    path('authorization/registration', SignupAPIView.as_view(), name = 'authorization-registration'),
    path('authorization/login', LoginAPIView.as_view(), name = 'authorization-login'),
    path('authorization/logout', LogoutAPIView.as_view(), name = 'authorization-logout'),
    path('authorization/refresh-token', CookieTokenRefreshView.as_view(), name = 'authorization-refresh-token'),
]