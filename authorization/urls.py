from django.urls import path

from .views import (SignupAPIView, LoginAPIView, LogoutAPIView, TokenRefreshView, 
                    DeleteUserAPIView, VerifyEmailAPIView, ResendEmailVerificationCodeAPIView)

urlpatterns = [
    path('authorization/registration', SignupAPIView.as_view(), name = 'authorization-registration'),
    path('authorization/login', LoginAPIView.as_view(), name = 'authorization-login'),
    path('authorization/verify-email', VerifyEmailAPIView.as_view(), name = 'authorization-verify-email'),
    path('authorization/resend-code', ResendEmailVerificationCodeAPIView.as_view(), name = 'authorization-resend-code'),
    path('authorization/logout', LogoutAPIView.as_view(), name = 'authorization-logout'),
    path('authorization/refresh-token', TokenRefreshView.as_view(), name = 'authorization-refresh-token'),
    path('authorization/delete-user', DeleteUserAPIView.as_view(), name = 'authorization-delete-user'),
]