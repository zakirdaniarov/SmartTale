import time

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from marketplace.models import Order
from .models import Notifications
from monitoring.models import Employee, STATUS_CHOICES
from chat.models import Message

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


# @receiver(post_delete, sender=Notifications)
# def notify_customers_on_delete(sender, instance, **kwargs):
#     time.sleep(SLEEP_TIME)
#     channel_layer = get_channel_layer()  # Use this function
#     async_to_sync(channel_layer.group_send)(
#         "branch",
#         {
#             "type": "get_notifications",
#         },
# )

@receiver(post_save, sender=Employee, dispatch_uid="employee-create")
def customer_status_changed(sender, instance, created, **kwargs):
    if created:
        if instance.status == STATUS_CHOICES[1][0]:
            title = "Приглашение в организацию"
            description = "Вы были приглашены в организацию {} на должность {}".format(instance.org.title, instance.job_title.title)
            Notifications.objects.create(
                type = 'Organization',
                title=title,
                description=description,
                recipient=instance.user,
                target_slug=instance.org.slug
            )

            user_name = f"{instance.user.id}-notifications"

            channel_layer = get_channel_layer()  # Use this function
            async_to_sync(channel_layer.group_send)(
                user_name,
                {
                    "type": "get_notifications_handler",
                }
            )

# @receiver(pre_save, sender=Order, dispatch_uid="order-apply")
# def order_apply_notification(sender, instance, **kwargs):
#     previous = Order.objects.filter(id=instance.id).first()
#     print(previous.org_applicants.all())
#     print(instance.org_applicants.all())
#     if previous and previous.org_applicants.all() != instance.org_applicants.all():
#         for org in instance.org_applicants.all():
#             if org not in previous.org_applicants.all():
#                 title = "Новая заявка на заказ"
#                 description = f"На Ваш заказ {instance.title} пришла новая заявка от {org.title}."
#                 Notifications.objects.create(
#                     title=title,
#                     description=description,
#                     recipient=instance.author
#                 )

#                 user_name = f"{instance.author.id}-notifications"
#                 channel_layer = get_channel_layer()
#                 async_to_sync(channel_layer.group_send)(
#                     user_name,
#                     {
#                         "type": "get_notifications_handler",
#                     }
#                 )

#                 # Notify the applicant organization
#                 title = "Заявка подана"
#                 description = f"Ваша организация {org.title} успешно отправила заявку на {instance.title}."
#                 Notifications.objects.create(
#                     title=title,
#                     description=description,
#                     recipient=org.founder
#                 )

#                 user_name = f"{org.founder.id}-notifications"
#                 async_to_sync(channel_layer.group_send)(
#                     user_name,
#                     {
#                         "type": "get_notifications_handler",
#                     }
#                 )

@receiver(pre_save, sender=Order, dispatch_uid="order-book")
def order_book_notification(sender, instance, **kwargs):
    previous = Order.objects.filter(id=instance.id).first()
    if previous:
        if previous.is_booked == False and instance.is_booked == True:
            title = "Заказ забронирован"
            description = f"Ваш заказ {instance.title} был забронирован."
            Notifications.objects.create(
                type = 'Order',
                title=title,
                description=description,
                recipient=instance.author,
                target_slug=instance.slug
            )

            user_name = f"{instance.author.id}-notifications"
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                user_name,
                {
                    "type": "get_notifications_handler",
                }
            )

@receiver(pre_save, sender=Order, dispatch_uid="order-finish")
def order_finish_notification(sender, instance, **kwargs):
    previous = Order.objects.filter(id=instance.id).first()
    if previous and previous.is_finished == False and instance.is_finished == True:
        # Notify the order author
        title = "Заказ готов"
        description = f"Ваш заказ - '{instance.title}' готов."
        Notifications.objects.create(
            type = 'Order',
            title=title,
            description=description,
            recipient=instance.author,
            target_slug = instance.slug
        )

        user_name = f"{instance.author.id}-notifications"
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user_name,
            {
                "type": "get_notifications_handler",
            }
        )

@receiver(pre_save, sender=Order, dispatch_uid="order-status-update")
def order_status_update_notification(sender, instance, **kwargs):
    # Notify the order author about the status change
    previous = Order.objects.filter(id=instance.id).first()
    if previous and previous.status != instance.status:
        title = "Статус заказа изменился!"
        description = f"Статус вашего заказа {instance.title} изменился c {previous.status} на {instance.status}."
        Notifications.objects.create(
            type = 'Order',
            title=title,
            description=description,
            recipient=instance.author,
            target_slug = instance.slug
        )

        user_name = f"{instance.author.id}-notifications"
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user_name,
            {
                "type": "get_notifications_handler",
            }
        )

# @receiver(post_save, sender=Message, dispatch_uid="message-send")
# def customer_status_changed(sender, instance, created, **kwargs):
#     if created:
#         title = "Новое сообщение"
#         description = "У вас новое сообщение от {}".format(instance.sender.first_name)
#         user = instance.conversation_id.initiator if instance.conversation_id.receiver == instance.sender else instance.conversation_id.receiver

#         Notifications.objects.create(
#             type = 'Chat',
#             title=title,
#             description=description,
#             recipient=user,
#             target_slug=instance.sender.slug
#         )

#         user_name = f"{user.id}-notifications"

#         channel_layer = get_channel_layer()  # Use this function
#         async_to_sync(channel_layer.group_send)(
#             user_name,
#             {
#                 "type": "get_notifications_handler",
#             }
#         )