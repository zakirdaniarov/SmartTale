from django.contrib import admin
from .models import Equipment, Order, Reviews, EquipmentCategory, OrderCategory, EquipmentImages, OrderImages


# Register your models here.
admin.site.register(Equipment)
admin.site.register(EquipmentCategory)
admin.site.register(EquipmentImages)
admin.site.register(Order)
admin.site.register(OrderCategory)
admin.site.register(OrderImages)
admin.site.register(Reviews)
