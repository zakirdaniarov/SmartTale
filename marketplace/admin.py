from django.contrib import admin

# Register your models here.

from .models import Equipment, EquipmentCategory, EquipmentImages

admin.site.register(Equipment)
admin.site.register(EquipmentCategory)
admin.site.register(EquipmentImages)
