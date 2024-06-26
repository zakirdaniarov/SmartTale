from django.db import models

# Create your models here.
from django.db import models
from authorization.models import UserProfile, Organization

TYPE_CHOICES = (
    ('Order', 'Order'),
    ('Equipment', 'Equipment'),
    ('Service', 'Service'),
    ('Organization', 'Organization'),
    ('Chat', 'Chat')
)

class Notifications(models.Model):
    type = models.CharField(max_length=50, default = 'Order')
    title = models.CharField(max_length=255)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    recipient = models.ForeignKey(UserProfile, related_name='recipient_name', on_delete=models.CASCADE)
    target_slug = models.SlugField(null = True, blank = True)

    def __str__(self):
        return f"{self.title} - {self.recipient.id}"
    