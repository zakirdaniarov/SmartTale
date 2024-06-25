from rest_framework import serializers
from .models import Notifications
from authorization.models import UserProfile, Organization

class UserSlugSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('slug',)

class OrgNotifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('slug', 'title')

class UserNotificationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(format="%d.%m.%Y %H:%M", read_only=True)
    org = OrgNotifSerializer()
    recipient = UserSlugSerializer()
    #title = serializers.CharField(max_length=255)
    #description = serializers.CharField(max_length=255)

    class Meta:
        model = Notifications
        fields = '__all__'
