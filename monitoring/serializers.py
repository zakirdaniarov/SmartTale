from rest_framework import serializers

from .models import Employee, JobTitle
from marketplace.models import Order
from authorization.models import Organization, UserProfile
from authorization.models import SUBCRIPTION_CHOICES

class JobTitleSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobTitle
        fields = ['title', 'description', 'slug', 'flag_create_jobtitle',
                  'flag_remove_jobtitle', 'flag_update_access',
                  'flag_add_employee', 'flag_remove_employee',
                  'flag_update_order', 'flag_delete_order', 'flag_employee_detail_access',
                  'flag_create_vacancy', 'flag_change_employee_job']
        read_only_fields = ('slug',)

    def create(self, validated_data):
        org = self.context['org']
        job_title = JobTitle.objects.create(org = org, **validated_data)
        return job_title

class MyEmployeeSerializer(serializers.ModelSerializer):
    organization = serializers.ReadOnlyField(source = 'org.title')
    job_title = serializers.ReadOnlyField(source = 'job_title.title')
    job_title = serializers.ReadOnlyField(source = 'job_title.slug')
    flag_create_jobtitle = serializers.ReadOnlyField(source = 'job_title.flag_create_jobtitle')
    flag_remove_jobtitle = serializers.ReadOnlyField(source = 'job_title.flag_remove_jobtitle')
    flag_update_access = serializers.ReadOnlyField(source = 'job_title.flag_update_access')
    flag_add_employee = serializers.ReadOnlyField(source = 'job_title.flag_add_employee')
    flag_remove_employee = serializers.ReadOnlyField(source = 'job_title.flag_remove_employee')
    flag_update_order = serializers.ReadOnlyField(source = 'job_title.flag_update_order')
    flag_delete_order = serializers.ReadOnlyField(source = 'job_title.flag_delete_order')
    flag_employee_detail_access = serializers.ReadOnlyField(source = 'job_title.flag_employee_detail_access')
    flag_create_vacancy = serializers.ReadOnlyField(source = 'job_title.flag_create_vacancy')
    flag_change_employee_job = serializers.ReadOnlyField(source = 'job_title.flag_change_employee_job')

    class Meta:
        model = Employee
        fields = ['active', 'organization', 'job_title', 'flag_create_jobtitle',
                  'flag_remove_jobtitle', 'flag_update_access',
                  'flag_add_employee', 'flag_remove_employee',
                  'flag_update_order', 'flag_delete_order', 'flag_employee_detail_access',
                  'flag_create_vacancy', 'flag_change_employee_job']

class MyOrganizationSerializer(serializers.ModelSerializer):
    founder = serializers.ReadOnlyField(source = 'founder.slug')    

    class Meta:
        model = Organization
        fields = ['title', 'slug', 'founder']

class OrganizationMonitoringSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ['title', 'description', 'phone_number', 'logo', 'active']

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
        fields = ['slug', 'title', 'owner', 'logo', 'phone_number', 'description', 'created_at']
        read_only_fields = ('slug', 'owner', 'created_at')

class OrganizationDetailSwaggerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ['title', 'logo', 'description', 'phone_number']

class OrganizationActiveSerializer(serializers.ModelSerializer):
    org_slug = serializers.ReadOnlyField(source = 'org.slug')
    class Meta:
        model = Employee
        fields = ['org_slug', 'active']

class MyOrganizationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['slug', 'title', 'description', 'logo']

class MyOrganizationActiveSerializer(serializers.Serializer):
    my_orgs = MyOrganizationListSerializer()
    orgs_active = OrganizationActiveSerializer()

class ProfileDetailSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source = 'user.email')

    class Meta:
        model = UserProfile
        fields = ['id', 'first_name', 'last_name', 'middle_name', 'phone_number', 'profile_image', 'email', 'slug']

class ProfileChangeSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'middle_name', 'phone_number', 'profile_image']

class OrderTitleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ['title', 'slug']

class InvitesSerializer(serializers.ModelSerializer):
    org = OrganizationDetailSerializer()
    job_title = JobTitleSerializer()

    class Meta:
        model = Employee
        fields = ('org', 'job_title')

class EmployeeListSerializer(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source = 'user.first_name')
    last_name = serializers.ReadOnlyField(source = 'user.last_name')
    middle_name = serializers.ReadOnlyField(source = 'user.middle_name')
    profile_image = serializers.ImageField(source = 'user.profile_image')
    email = serializers.ReadOnlyField(source = 'user.user.email')
    user_slug = serializers.ReadOnlyField(source = 'user.slug')
    order = OrderTitleSerializer(many = True, read_only = True)
    job_title = serializers.ReadOnlyField(source = 'job_title.title')

    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'middle_name', 'email', 'user_slug', 'profile_image',
                  'order', 'job_title', 'status']
        extra_kwargs = {
            'profile_image': {
                'allow_null': True,
                'allow_blank': True
            }
        }
class UserEmployeeSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source = 'user.email')
    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'middle_name', 'email', 'phone_number', 'slug', 'profile_image')

class EmployeeDetailSerializer(serializers.ModelSerializer):
    user = UserEmployeeSerializer()
    job_title = JobTitleSerializer()

    class Meta:
        model = Employee
        fields = ['user', 'job_title']
        
# For openapi
class EmployeeCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    org_slug = serializers.SlugField()
    jt_slug = serializers.SlugField()

class EmployeeExitSerializer(serializers.Serializer):
    org_slug = serializers.SlugField()


class EmployeeDeleteSerializer(serializers.Serializer):
    user_slug = serializers.SlugField()

class EmployeeChangeSerializer(serializers.Serializer):
    jt_slug = serializers.CharField()
class SubscribeResponseSerializer(serializers.Serializer):
    new_sub_dt = serializers.DateTimeField()

class SubscribeRequestSerializer(serializers.Serializer):
    subscription = serializers.CharField(max_length = 20)