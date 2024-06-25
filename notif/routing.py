from django.urls import path
from .consumers import NotificationConsumer

websocket_urlpatterns = [
    path('ws/user/<user_slug>', NotificationConsumer.as_asgi()),
]