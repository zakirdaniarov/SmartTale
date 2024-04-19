from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from autoslug import AutoSlugField

from .utils import LowercaseEmailField

GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
)

# Create your models here.
class UserManager(BaseUserManager):

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError()
        email = self.normalize_email(email)
        user = self.model(email = email, **extra_fields)
        user.set_password(password)
        user.save()
        return user
    
class User(AbstractBaseUser, PermissionsMixin):
    email = LowercaseEmailField(unique = True)
    is_staff = models.BooleanField(default = False)
    is_superuser = models.BooleanField(default = False)
    is_verified = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add = True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, verbose_name = 'user', related_name = 'user_profile', on_delete = models.CASCADE)
    name = models.CharField(max_length = 50)
    lastname = models.CharField(max_length = 50)
    middlename = models.CharField(max_length = 50)
    profile_image = models.ImageField(upload_to = 'smarttale/user_profile', blank = True, null = True, max_length = 500)
    slug = AutoSlugField(populate_from = lambda instance: f"{instance.name}-{instance.lastname}",
                         unique_with = ['name', 'lastname'],
                         slugify=lambda value: value.replace(' ','-'), unique = True, always_update = True)
    gender = models.CharField(max_length = 6, choices = GENDER_CHOICES, blank = True, null = True, default = None)
    birthday = models.DateField(null = True, default = None)
    phone_number = models.CharField(max_length = 20, blank = True, null = True, default = None)
    subscription = models.DateTimeField(blank = True, null = True, default = None)
    created_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return f"Name: {self.lastname} {self.name}; Email: {self.user}; Slug: {self.slug}"

class Organization(models.Model):
    founder = models.ForeignKey(UserProfile, verbose_name = 'user', related_name = 'founder_organizations', on_delete = models.DO_NOTHING)
    owner = models.ForeignKey(UserProfile, verbose_name = 'user', related_name = 'owner_organizations', on_delete = models.DO_NOTHING)
    title = models.CharField(max_length = 100)
    slug = AutoSlugField(populate_from = 'title', unique = True, always_update = True)
    phone_number = models.CharField(max_length = 20, blank = True, null = True, default = None)
    subscription = models.DateTimeField(blank = True, null = True, default = None)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return f"Title: {self.title}; Email: {self.user}; Slug: {self.slug}"