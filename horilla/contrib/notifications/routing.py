"""
WebSocket URL routing configuration for notifications.

This module defines the WebSocket URL patterns for real-time notification
delivery using Django Channels.
"""

# First party imports (Horilla)
from horilla.urls import re_path

# Local imports
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
]
