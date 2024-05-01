from django.contrib import admin
from .models import User, UserProfile, ConfirmationCode, Organization

# Register your models here.
admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(ConfirmationCode)
admin.site.register(Organization)
