import time

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from marketplace.models import Order
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

@receiver(post_save, sender=Order, dispatch_uid="order-apply")
def order_apply_notification(sender, instance, created, **kwargs):
    if created:
        order = instance
        applicant_org = instance.org_applicants

        # Notify the order author
        title = "New Order Application"
        description = f"Your order '{order.title}' has received a new application from {applicant_org.title}."
        Notifications.objects.create(
            title=title,
            description=description,
            recipient=order.author
        )

        user_name = f"{order.author.id}-notifications"
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user_name,
            {
                "type": "get_notifications_handler",
            }
        )

        # Notify the applicant organization
        title = "Application Submitted"
        description = f"Your organization '{applicant_org.title}' has successfully applied for the order '{order.title}'."
        Notifications.objects.create(
            title=title,
            description=description,
            recipient=applicant_org.founder
        )

        user_name = f"{applicant_org.founder.id}-notifications"
        async_to_sync(channel_layer.group_send)(
            user_name,
            {
                "type": "get_notifications_handler",
            }
        )

@receiver(post_save, sender=Order, dispatch_uid="order-book")
def order_book_notification(sender, instance, **kwargs):
    if instance.is_booked:
        # Notify the order author
        title = "Order Booked"
        description = f"Your order '{instance.title}' has been booked."
        Notifications.objects.create(
            title=title,
            description=description,
            recipient=instance.author
        )

        user_name = f"{instance.author.id}-notifications"
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user_name,
            {
                "type": "get_notifications_handler",
            }
        )

@receiver(post_save, sender=Order, dispatch_uid="order-finish")
def order_finish_notification(sender, instance, **kwargs):
    if instance.is_finished:
        # Notify the order author
        title = "Order Finished"
        description = f"Your order '{instance.title}' has been marked as finished."
        Notifications.objects.create(
            title=title,
            description=description,
            recipient=instance.author
        )

        user_name = f"{instance.author.id}-notifications"
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user_name,
            {
                "type": "get_notifications_handler",
            }
        )

@receiver(post_save, sender=Order, dispatch_uid="order-status-update")
def order_status_update_notification(sender, instance, **kwargs):
    # Notify the order author about the status change
    title = "Order Status Updated"
    description = f"The status of your order '{instance.title}' has been updated to {instance.status}."
    Notifications.objects.create(
        title=title,
        description=description,
        recipient=instance.author
    )

    user_name = f"{instance.author.id}-notifications"
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        user_name,
        {
            "type": "get_notifications_handler",
        }
    )
