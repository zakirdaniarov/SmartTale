from rest_framework import serializers

from .models import Employee, JobTitle
from marketplace.models import Order
from authorization.models import Organization, UserProfile
from authorization.models import SUBCRIPTION_CHOICES

class JobTitleSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields['title'].read_only = True
            self.fields['description'].read_only = True

    class Meta:
        model = JobTitle
        fields = ['title', 'description', 'flag_create_jobtitle',
                  'flag_remove_jobtitle', 'flag_update_access',
                  'flag_add_employee', 'flag_remove_employee',
                  'flag_update_order', 'flag_delete_order']

    def create(self, validated_data):
        org = self.context['org']
        job_title = JobTitle.objects.create(org = org, **validated_data)
        return job_title


class OrganizationMonitoringSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ['title', 'description', 'logo', 'active']

    def create(self, validated_data):
        user = self.context['user']
        if user.sub_type == SUBCRIPTION_CHOICES[2][0] and validated_data['active']:
            old_active_org = Organization.objects.filter(owner = user, active = True).first()
            if old_active_org:
                old_active_org.active = False
                old_active_org.save()
        elif user.sub_type in (SUBCRIPTION_CHOICES[1][0], SUBCRIPTION_CHOICES[0][0]):
            validated_data['active'] = True
        org = Organization.objects.create(founder = user, owner = user, **validated_data)
        return org

class OwnerSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = ['slug', 'first_name', 'last_name', 'profile_image']

class OrganizationDetailSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = ['slug', 'title', 'owner', 'logo', 'description', 'created_at']

class OrganizationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ['slug', 'title', 'logo', 'description', 'active']

class ProfileDetailSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source = 'user.email')

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'middle_name', 'phone_number', 'profile_image', 'email', 'slug']

class ProfileChangeSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'middle_name', 'phone_number', 'profile_image']

class OrderTitleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ['title', 'slug']

class EmployeeListSerializer(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source = 'user.first_name')
    last_name = serializers.ReadOnlyField(source = 'user.last_name')
    middle_name = serializers.ReadOnlyField(source = 'user.middle_name')
    email = serializers.ReadOnlyField(source = 'user.user.email')
    user_slug = serializers.ReadOnlyField(source = 'user.slug')
    order = OrderTitleSerializer(many = True, read_only = True)
    job_title = serializers.ReadOnlyField(source = 'job_title.title')

    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'middle_name', 'email', 'user_slug',
                  'order', 'job_title','status']
        
class EmployeeDetailSerializer(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source = 'user.first_name')
    last_name = serializers.ReadOnlyField(source = 'user.last_name')
    middle_name = serializers.ReadOnlyField(source = 'user.middle_name')
    email = serializers.ReadOnlyField(source = 'user.user.email')
    user_slug = serializers.ReadOnlyField(source = 'user.slug')
    phone_number = serializers.ReadOnlyField(source = 'user.phone_number')
    job_title = serializers.ReadOnlyField(source = 'job_title.title')
    job_title_flag_create_jobtitle = serializers.ReadOnlyField(source = 'job_title.flag_create_jobtitle')
    job_title_flag_remove_jobtitle = serializers.ReadOnlyField(source = 'job_title.flag_remove_jobtitle')
    job_title_flag_update_access = serializers.ReadOnlyField(source = 'job_title.flag_update_access')
    job_title_flag_add_employee = serializers.ReadOnlyField(source = 'job_title.flag_add_employee')
    job_title_flag_remove_employee = serializers.ReadOnlyField(source = 'job_title.flag_remove_employee')
    job_title_flag_update_order = serializers.ReadOnlyField(source = 'job_title.flag_update_order')
    job_title_flag_delete_order = serializers.ReadOnlyField(source = 'job_title.flag_delete_order')

    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'middle_name', 'email', 'phone_number', 'user_slug',
                  'job_title', 'job_title_flag_create_jobtitle',
                  'job_title_flag_remove_jobtitle', 'job_title_flag_update_access',
                  'job_title_flag_add_employee', 'job_title_flag_remove_employee',
                  'job_title_flag_update_order', 'job_title_flag_delete_order']
        
# For openapi
class EmployeeCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    org_slug = serializers.SlugField()
    jt_slug = serializers.SlugField()

class EmployeeDeleteSerializer(serializers.Serializer):
    user_slug = serializers.SlugField()

class SubscribeResponseSerializer(serializers.Serializer):
    new_sub_dt = serializers.DateTimeField()

class SubscribeRequestSerializer(serializers.Serializer):
    subscription = serializers.CharField(max_length = 20)