from django.apps import AppConfig


class NotifConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notif'

    def ready(self):
        import notif.signals