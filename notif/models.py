from django.db import models

# Create your models here.
from django.db import models
from authorization.models import UserProfile


class Notif(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    recipient = models.ForeignKey(UserProfile, related_name='recipient_name', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} - {self.recipient.id}"