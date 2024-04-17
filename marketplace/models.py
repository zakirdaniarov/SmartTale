from django.db import models
from autoslug import AutoSlugField
from authorization.models import UserProfile, Organization


class EquipmentCategory(models.Model):
    title = models.CharField(max_length=60)

    def __str__(self):
        return self.title


class Equipment(models.Model):
    title = models.CharField(max_length=70)
    category = models.ForeignKey(EquipmentCategory, related_name='equipment_ads', on_delete=models.DO_NOTHING)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(max_length=1000, null=True)
    phone_number = models.CharField(max_length=20)
    author = models.ForeignKey(UserProfile, related_name='equipment_ads', on_delete=models.CASCADE)
    liked_by = models.ManyToManyField(UserProfile, blank=True, related_name='liked_equipments')
    hide = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


class EquipmentImages(models.Model):
    equipment = models.ForeignKey(Equipment, related_name='images', on_delete=models.CASCADE)
    images = models.ImageField(verbose_name='Equipment images', upload_to='Equipment images',
                               blank=True, null=True)

    def __str__(self):
        return f'These images for {self.equipment.title}'


class OrderCategory(models.Model):
    title = models.CharField(max_length=60)

    def __str__(self):
        return self.title


STATUS = (('New', 'New'), ('In Progress', 'In Progress'), ('Checking', 'Checking'), ('Sent', 'Sent'),('Arrived', 'Arrived'),)


class Order(models.Model):
    title = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)
    category = models.ForeignKey(OrderCategory, related_name='orders', on_delete=models.DO_NOTHING)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(max_length=1000, null=True)
    size = models.CharField(max_length=100)
    deadline = models.DateField()
    phone_number = models.CharField(max_length=20)
    hide = models.BooleanField(default=False)
    is_booked = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='New')
    liked_by = models.ManyToManyField(UserProfile, blank=True, related_name='liked_orders')
    author = models.ForeignKey(UserProfile, related_name='order_ads', on_delete=models.CASCADE)
    org_work = models.ForeignKey(Organization, related_name='received_orders')

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


class OrderImages(models.Model):
    order = models.ForeignKey(Order, related_name='images', on_delete=models.CASCADE)
    images = models.ImageField(verbose_name='Order images', upload_to='Order images',
                               blank=True, null=True)

    def __str__(self):
        return f'These images for {self.order.title}'

