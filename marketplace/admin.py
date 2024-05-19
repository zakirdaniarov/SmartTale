from django.contrib import admin
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages
from .models import ServiceImages, Service, ServiceCategory, Size

# Register your models here.
admin.site.register(Equipment)
admin.site.register(EquipmentCategory)
admin.site.register(EquipmentImages)
admin.site.register(Order)
admin.site.register(OrderCategory)
admin.site.register(OrderImages)
admin.site.register(Reviews)
admin.site.register(Service)
admin.site.register(ServiceCategory)
admin.site.register(ServiceImages)
admin.site.register(Size)
