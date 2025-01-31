"""
ASGI config for smarttale project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarttale.settings")
django_asgi_app = get_asgi_application()

import chat.routing
# from chat.channelsmiddleware import JwtAuthMiddlewareStack
from channels_auth_token_middlewares.middleware import QueryStringSimpleJWTAuthTokenMiddleware


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            QueryStringSimpleJWTAuthTokenMiddleware(
                URLRouter(
                    # [
                    chat.routing.websocket_urlpatterns
                    # ]
                )
            ),
        ),
    }
)