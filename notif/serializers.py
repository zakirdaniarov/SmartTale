from rest_framework import serializers
from .models import Notifications
from authorization.models import UserProfile

class UserSlugSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('slug',)


class UserNotificationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(format="%d.%m.%Y %H:%M", read_only=True)
    recipient = UserSlugSerializer()
    #title = serializers.CharField(max_length=255)
    #description = serializers.CharField(max_length=255)

    class Meta:
        model = Notifications
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['title'] = ret['title']
        ret['description'] = ret['description']
        return ret