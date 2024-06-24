# import json

# from channels.db import database_sync_to_async
# from channels.generic.websocket import WebsocketConsumer
# from asgiref.sync import sync_to_async
# from django.utils import timezone

# from .models import Notif
# from authorization.models import UserProfile

# class NotificationConsumer(WebsocketConsumer):

#     def connect(self):
#         print("WebSocket connected!")
#         self.user_slug = self.scope["url_route"]["kwargs"]["user_slug"]
#         self.user = self.get_user(self.user_slug)
#         print(self.user)
#         self.user_group_name = f"{self.user_slug}'s-notifications"
#         self.channel_layer.group_add(self.user_group_name, self.channel_name)

#         self.accept()
#         self.get_notifications()

#     @database_sync_to_async
#     def get_user(self, user_slug):
#         return UserProfile.objects.get(slug = user_slug)

#     def disconnect(self, close_code):
#         # Disconnect from group
#         self.channel_layer.group_discard(
#             self.user_group_name, self.channel_name
#         )

#     def get_notifications(self):
#         notifications = Notif.objects.filter(recipient=self.user.id, read=False).order_by('-timestamp')
#         notifications_list = []
#         for notification in notifications:
#             notification.timestamp = timezone.localtime(notification.timestamp)
#             notifications_list.append(
#                 {
#                     "id": notification.id,
#                     "title": notification.title,
#                     "description": notification.description,
#                     "timestamp": notification.timestamp.strftime("%H:%M"),
#                 }
#             )
#             notification.read = True
#             notification.save
#         self.send(text_data=json.dumps({"notifications": notifications_list}))

#     def get_notifications_handler(self, event):
#         self.get_notifications()

#     def receive(self, text_data):
#         ...
#         # text_data_json = json.loads(text_data)

#     def receive_get_notifications(self, event):
#         self.get_notifications()

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone

from .models import Notifications
from authorization.models import UserProfile

class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        print("WebSocket connected!")
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.user = await self.get_user(self.user_id)
        jwt_user = self.scope['user']
        # print(self.user)
        self.user_group_name = f"{self.user_id}-notifications"
        jwt_user = await self.get_jwt_user(jwt_user)
        if self.user == jwt_user:
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)

            await self.accept()
            await self.get_notifications()

    @database_sync_to_async
    def get_jwt_user(self, jwt_user):
        return jwt_user.user_profile

    @database_sync_to_async
    def get_user(self, user_id):
        return UserProfile.objects.get(id = user_id)

    async def disconnect(self, close_code):
        # Disconnect from group
        self.channel_layer.group_discard(
            self.user_group_name, self.channel_name
        )

    async def get_notifications(self):
        notifications = await sync_to_async(list, thread_sensitive=True)(
            Notifications.objects.filter(recipient=self.user.id, read=False).order_by('-timestamp')
        )
        notifications_list = []
        for notification in notifications:
            notification.timestamp = timezone.localtime(notification.timestamp)
            notifications_list.append(
                {
                    "id": notification.id,
                    "title": notification.title,
                    "description": notification.description,
                    "timestamp": notification.timestamp.strftime("%H:%M"),
                }
            )
            notification.read = True
            await sync_to_async(notification.save, thread_sensitive=True)()
        await self.send(text_data=json.dumps({"notifications": notifications_list}))

    async def get_notifications_handler(self, event):
        await self.get_notifications()

    async def receive(self, text_data):
        ...
        # text_data_json = json.loads(text_data)

    async def receive_get_notifications(self, event):
        await self.get_notifications()