from django.urls import path

from .views import *

urlpatterns = [
    path('notifications/delete/<int:pk>/', NotificationDeleteView.as_view(), name='delete'),
    path('notifications/delete/all/', NotificationAllDeleteView.as_view(), name='delete-all'),
    path('notifications/list/', UserNotificationListView.as_view(), name='notifications')
]