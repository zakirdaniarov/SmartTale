from pyfcm import FCMNotification
from django.conf import settings

API_KEY = 'AIzaSyAOeftS1qYUuUcQ40OWEQEJ3DzQ48530wI'


def send_push_notification():
    push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)

    message = push_service.notify_single_device(
        "geg"
    )

    return message
