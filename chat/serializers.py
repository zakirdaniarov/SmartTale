from rest_framework import serializers

from .models import Conversation, Message
from authorization.models import UserProfile

class UserChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'slug', 'profile_image']
        extra_kwagrs = {'first_name': {'read_only': True}, 
                        'last_name': {'read_only': True},
                        'profile_image': {'read_only': True}}

class MessageSerializer(serializers.ModelSerializer):
    sender = UserChatSerializer()
    class Meta:
        model = Message
        fields = ['sender', 'text', 'attachment', 'timestamp']


class ConversationListSerializer(serializers.ModelSerializer):
    initiator = UserChatSerializer()
    receiver = UserChatSerializer()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['initiator', 'receiver', 'last_message']

    def get_last_message(self, instance):
        message = instance.message_set.first()
        return message.text


class ConversationSerializer(serializers.ModelSerializer):
    initiator = UserChatSerializer()
    receiver = UserChatSerializer()
    message_set = MessageSerializer(many=True)

    class Meta:
        model = Conversation
        fields = ['initiator', 'receiver', 'message_set']