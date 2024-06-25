from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from drf_yasg.utils import swagger_auto_schema

from authorization.models import UserProfile
from .models import Conversation, Message
from .serializers import ConversationListSerializer, ConversationSerializer, MessageSerializer

# Create your views here.

class ConversationStartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Chat"],
        operation_summary = "Начать переписку",
        operation_description = "Предоставляет возможность к созданию чата с другим пользователем",
        responses = {
            200: ConversationSerializer,
            404: "Not found",
        }
    )   
    def post(self, request):
        data = request.data
        user_slug = data['user_slug']
        try:
            participant = UserProfile.objects.get(slug = user_slug)
        except UserProfile.DoesNotExist:
            return Response({'message': 'You cannot chat with a non existent user'})

        conversation = Conversation.objects.filter(Q(initiator=request.user.user_profile, receiver=participant) |
                                                Q(initiator=participant, receiver=request.user.user_profile))
        if conversation.exists():
            return redirect(reverse('getconversation', args=(conversation[0].id,)))
        else:
            conversation = Conversation.objects.create(initiator=request.user.user_profile, receiver=participant)
            return Response(ConversationSerializer(instance=conversation).data)


class MessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Chat"],
        operation_summary = "Открыть переписку с пользователем.",
        operation_description = "Предоставляет доступ к переписке с другим пользователем.",
        responses = {
            200: ConversationSerializer,
            404: "Not found",
        }
    )
    def get(self, request, convo_id):
        conversation = Conversation.objects.filter(id=convo_id)
        if not conversation.exists():
            return Response({'message': 'Conversation does not exist'})
        else:
            serializer = ConversationSerializer(instance=conversation[0])
            return Response(serializer.data)

class SendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Chat"],
        operation_summary = "Отправить сообщение.",
        operation_description = "Предоставляет доступ к отправке сообщения другому пользователю.",
        responses = {
            200: MessageSerializer,
            404: "Not found",
        }
    )
    def get(self, request, user_slug):
        data = request.data
        try:
            participant = UserProfile.objects.get(slug = user_slug)
        except UserProfile.DoesNotExist:
            return Response({'message': 'You cannot chat with a non existent user'})

        conversation = Conversation.objects.filter(Q(initiator=request.user.user_profile, receiver=participant) |
                                                Q(initiator=participant, receiver=request.user.user_profile)).first()
        if not conversation:
            conversation = Conversation.objects.create(initiator=request.user.user_profile, receiver=participant)
        attachment = data.get('attachment', None)
        message = Message.objects.create(sender = request.user.user_profile, text = data['text'], conversation_id = conversation, attachment = attachment)
        return Response(MessageSerializer(instance=message).data)


class ConversationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Chat"],
        operation_summary = "Список чатов пользователя",
        operation_description = "Предоставляет доступ к чатам пользователя.",
        responses = {
            200: ConversationSerializer,
            404: "Not found",
        }
    )
    def get(self, request):
        conversation_list = Conversation.objects.filter(Q(initiator=request.user.user_profile) |
                                                        Q(receiver=request.user.user_profile))
        serializer = ConversationListSerializer(instance=conversation_list, many=True)
        return Response(serializer.data)
