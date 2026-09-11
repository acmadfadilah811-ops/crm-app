"""
Serializers for notifications models
"""

# Third-party imports (Django)
from rest_framework import serializers

# First party imports (Horilla)
from horilla.contrib.core.api.serializers import HorillaUserSerializer

# Local imports
from ..models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    sender_details = HorillaUserSerializer(source="sender", read_only=True)
    user_details = HorillaUserSerializer(source="user", read_only=True)

    class Meta:
        """Meta class for NotificationSerializer"""

        model = Notification
        fields = "__all__"

    def validate(self, data):
        """
        Validate notification data
        """
        # Validate message field is not empty
        if "message" in data and not data["message"].strip():
            raise serializers.ValidationError({"message": "Message cannot be empty"})

        # Validate URL format if provided
        if "url" in data and data["url"] and not data["url"].startswith("/"):
            raise serializers.ValidationError(
                {"url": "URL must be a relative path starting with /"}
            )

        return data
