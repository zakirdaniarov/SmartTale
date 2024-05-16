from django.db import models
from autoslug import AutoSlugField
from authorization.models import UserProfile, Organization
from django.core.validators import MinValueValidator, MaxValueValidator


class EquipmentCategory(models.Model):
    title = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


class Equipment(models.Model):
    title = models.CharField(max_length=70)
    category = models.ForeignKey(EquipmentCategory, related_name='equipments', null=True, blank=True, on_delete=models.DO_NOTHING)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(max_length=1000, null=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(max_length=70, blank=True, unique=True)
    author = models.ForeignKey(UserProfile, related_name='equipment_ads', on_delete=models.CASCADE)
    liked_by = models.ManyToManyField(UserProfile, blank=True, related_name='liked_equipment')
    hide = models.BooleanField(default=False)
    sold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


class EquipmentImages(models.Model):
    equipment = models.ForeignKey(Equipment, related_name='images', on_delete=models.CASCADE)
    images = models.ImageField(verbose_name='Equipment images', upload_to='Equipment images',
                               blank=True, null=True)

    def __str__(self):
        return f'These images for {self.equipment.title}, slug: {self.equipment.slug}'


class ServiceCategory(models.Model):
    title = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


class Service(models.Model):
    title = models.CharField(max_length=70)
    category = models.ManyToManyField(ServiceCategory, related_name='services', blank=True)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(max_length=1000, null=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(max_length=70, blank=True, unique=True)
    author = models.ForeignKey(UserProfile, related_name='service_ads', on_delete=models.CASCADE)
    liked_by = models.ManyToManyField(UserProfile, blank=True, related_name='liked_services')
    hide = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


class ServiceImages(models.Model):
    service = models.ForeignKey(Service, related_name='images', on_delete=models.CASCADE)
    images = models.ImageField(verbose_name='Service images', upload_to='Service images',
                               blank=True, null=True)

    def __str__(self):
        return f'These images for {self.service.title}, slug: {self.service.slug}'


class OrderCategory(models.Model):
    title = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


STATUS = (('Waiting', 'Waiting'), ('Process', 'Process'), ('Checking', 'Checking'), ('Sending', 'Sending'), ('Arrived', 'Arrived'),)
SIZE = (('40', '40'), ('42', '42'), ('46', '46'), ('48', '48'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'))

class Order(models.Model):
    title = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from='title', unique=True, always_update=True)
    category = models.ForeignKey(OrderCategory, related_name='orders', null=True, blank=True, on_delete=models.DO_NOTHING)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(max_length=1000, null=True)
    size = models.CharField(max_length=10, choices=SIZE, default='40')
    deadline = models.DateField()
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(max_length=70, blank=True, unique=True)
    hide = models.BooleanField(default=False)
    is_booked = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='Waiting')
    liked_by = models.ManyToManyField(UserProfile, blank=True, related_name='liked_orders')
    author = models.ForeignKey(UserProfile, related_name='order_ads', on_delete=models.CASCADE)
    org_work = models.ForeignKey(Organization, related_name='received_orders', blank=True, null=True, on_delete=models.DO_NOTHING)
    org_applicants = models.ManyToManyField(Organization, related_name='applied_orders', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    booked_at = models.DateTimeField(blank=True, null=True)
    is_finished = models.BooleanField(default=False)
    finished_at = models.DateTimeField(blank=True, null=True)
    arrived_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.title}, slug: {self.slug}"


class OrderImages(models.Model):
    order = models.ForeignKey(Order, related_name='images', on_delete=models.CASCADE)
    images = models.ImageField(verbose_name='Order images', upload_to='Order images',
                               blank=True, null=True)

    def __str__(self):
        return f'These images for {self.order.title}, slug: {self.order.slug}'


class Reviews(models.Model):
    order = models.OneToOneField(Order, related_name='order_reviews', on_delete=models.CASCADE)
    reviewer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='reviews')
    review_text = models.TextField()
    rating = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)], default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.reviewer} on {self.order}'
