from django.urls import path
from . import views

urlpatterns = [
    path('conversation/start/', views.ConversationStartAPIView.as_view(), name='start-conversation'),
    path('messages/<int:convo_id>/', views.MessageAPIView.as_view(), name='get-conversation'),
    path('conversations/', views.ConversationListAPIView.as_view(), name='conversations')
]