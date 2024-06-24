from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import UserNotificationSerializer
from .models import Notif

class NotificationDeleteView(APIView):
    def delete(self, request, pk, *args, **kwargs):
        try:
            notification = Notif.objects.get(pk=pk, recipient=request.user.user_profile)
            notification.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notif.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class NotificationAllDeleteView(APIView):

    def delete(self, request, *args, **kwargs):
        try:
            notifications = Notif.objects.filter(recipient=request.user.user_profile)
            notifications.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notif.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
class UserNotificationListView(APIView):
    serializer_class = UserNotificationSerializer

    def get(self, request, *args, **kwargs):
        notifications = Notif.objects.filter(recipient=request.user.user_profile)
        serializer = self.serializer_class(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)