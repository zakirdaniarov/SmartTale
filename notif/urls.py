from django.urls import path

from .views import *

urlpatterns = [
    path('notifications/delete/<int:pk>/', NotificationDeleteView.as_view(), name='delete'),
    path('notifications/delete/all/', NotificationAllDeleteView.as_view(), name='delete-all'),
    path('notifications/list/', UserNotificationListView.as_view(), name='notifications'),
    path('notification/read/<int:notif_id>/', ReadNotificationView.as_view(), name='notificationread'),
    path('notificationslist/read/', ReadNotificationListView.as_view(), name='notificationslistread')
]