from django.db import models

from autoslug import AutoSlugField

from authorization.models import Organization, UserProfile
from marketplace.models import Order
# Create your models here.

STATUS_CHOICES = (
    ('Авторизован', 'Авторизован'),
    ('Ожидает подтверждения', 'Ожидает подтверждения')
)

class JobTitle(models.Model):

    org = models.ForeignKey(Organization, verbose_name = 'org', related_name = 'jobs', on_delete = models.CASCADE)
    title = models.CharField(max_length = 50)
    description = models.TextField()
    slug = AutoSlugField(populate_from = 'title', unique = True, always_update = True, default = 'job-title')
    flag_create_jobtitle = models.BooleanField(default = False)
    flag_remove_jobtitle = models.BooleanField(default = False)
    flag_update_access = models.BooleanField(default = False)
    flag_add_employee = models.BooleanField(default = False)
    flag_update_order = models.BooleanField(default = False)
    flag_delete_order = models.BooleanField(default = False)
    flag_remove_employee = models.BooleanField(default = False)
    flag_employee_detail_access = models.BooleanField(default = False)
    flag_create_vacancy = models.BooleanField(default = False)
    flag_change_employee_job = models.BooleanField(default = False)

    def __str__(self):
        return "{}-{}-{}".format(self.org.title, self.title, self.slug)
    
    class Meta:
        unique_together = ('org', 'title')

class Employee(models.Model):
    user = models.ForeignKey(UserProfile, verbose_name = 'user', related_name = 'working_orgs', on_delete = models.CASCADE)
    org = models.ForeignKey(Organization, verbose_name = 'org', related_name = 'employees', on_delete = models.CASCADE)
    order = models.ManyToManyField(Order, verbose_name = 'order', related_name = 'workers', blank=True)
    job_title = models.ForeignKey(JobTitle, verbose_name = 'job_title', related_name = 'jt_employees', null = True, blank = True, on_delete = models.SET_NULL)
    status = models.CharField(max_length = 25, choices = STATUS_CHOICES, default = 'Авторизован')
    active = models.BooleanField(default = False)
    created_at = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return "Organization: {}; User: {}".format(self.org, self.user)
