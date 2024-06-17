from firebase_admin import messaging

def send_fcm_notification(token, title, body, data=None):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
        data=data
    )
    response = messaging.send(message)
    return response

