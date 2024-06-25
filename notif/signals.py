import time

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Notifications
from monitoring.models import Employee, STATUS_CHOICES

SLEEP_TIME = 3




@receiver(post_save, sender=Notifications)
def notify_customers(sender, instance, **kwargs):
    """
    Updates notifications on customer side.
    """
    time.sleep(SLEEP_TIME)
    channel_layer = get_channel_layer()  # Use this function
    async_to_sync(channel_layer.group_send)(
        "branch",
        {
            "type": "get_notifications",
        },
    )


@receiver(post_delete, sender=Notifications)
def notify_customers_on_delete(sender, instance, **kwargs):
    time.sleep(SLEEP_TIME)
    channel_layer = get_channel_layer()  # Use this function
    async_to_sync(channel_layer.group_send)(
        "branch",
        {
            "type": "get_notifications",
        },
    )

@receiver(post_save, sender=Employee, dispatch_uid="employee-create")
def customer_status_changed(sender, instance, created, **kwargs):
    if created:
        if instance.status == STATUS_CHOICES[1][0]:
            title = "Приглашение в организацию"
            description = "Вы были приглашены в организацию {} на должность {}".format(instance.org.title, instance.job_title.title)
            Notifications.objects.create(
                title=title,
                description=description,
                recipient=instance.user
            )

            user_name = f"{instance.user.id}-notifications"

            channel_layer = get_channel_layer()  # Use this function
            async_to_sync(channel_layer.group_send)(
                user_name,
                {
                    "type": "get_notifications_handler",
                }
            )