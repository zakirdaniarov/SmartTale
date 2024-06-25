from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import UserNotificationSerializer
from .models import Notifications

class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        try:
            notification = Notifications.objects.get(pk=pk, recipient=request.user.user_profile)
            notification.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notifications.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class NotificationAllDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        try:
            notifications = Notifications.objects.filter(recipient=request.user.user_profile)
            notifications.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notifications.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
class UserNotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationSerializer

    def get(self, request, *args, **kwargs):
        notifications = Notifications.objects.filter(recipient=request.user.user_profile).order_by('-timestamp')
        serializer = self.serializer_class(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ReadNotificationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationSerializer

    def put(self, request, notif_id, *args, **kwargs):
        notification = Notifications.objects.filter(id = notif_id, recipient=request.user.user_profile, read = False).first()
        if notification:
            notification.read = True
            notification.save()
            return Response({"Success": "Уведомление прочитано."}, status=status.HTTP_200_OK)
        else:
            return Response({"Message": "Нет такого уведомления или оно уже прочитано."}, status=status.HTTP_400_BAD_REQUEST)
        
class ReadNotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationSerializer

    def put(self, request, *args, **kwargs):
        notifications = Notifications.objects.filter(recipient=request.user.user_profile, read = False)
        for notification in notifications:
            notification.read = True
            notification.save()
        return Response({"Success": "Уведомления прочитаны."}, status=status.HTTP_200_OK)