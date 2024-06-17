# # tasks.py
# from datetime import timedelta
# from django.utils import timezone
# from django_q.tasks import schedule


# def check_and_auto_finish_orders():
#     from .models import Order

#     # Calculate the threshold date (seven days ago)
#     threshold_date = timezone.now() - timedelta(days=7)

#     # Query orders that are arrived but not finished manually within seven days
#     orders_to_auto_finish = Order.objects.filter(status='Arrived', is_finished=False, arrived_at__lte=threshold_date)

#     # Auto finish each order
#     for order in orders_to_auto_finish:
#         order.is_finished = True
#         order.finished_at = timezone.now()
#         order.save()


# # Schedule the task to run every day
# schedule('tasks.check_and_auto_finish_orders', q_options={'schedule_type': 'D', 'minutes': 1})
