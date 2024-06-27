from rest_framework import serializers
from .models import Notifications
from authorization.models import UserProfile, Organization

class UserSlugSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('slug',)

class UserNotificationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(format="%d.%m.%Y %H:%M", read_only=True)
    recipient = UserSlugSerializer()

    class Meta:
        model = Notifications
        fields = '__all__'
