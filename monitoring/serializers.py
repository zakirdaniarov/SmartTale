from rest_framework import serializers

from .models import Employee, JobTitle
from marketplace.models import Order
from authorization.models import Organization, UserProfile

class JobTitleSeriailizer(serializers.ModelSerializer):

    class Meta:
        model = JobTitle
        fields = ['org', 'title', 'description']

    def create(self, validated_data):
        validated_data.pop('org')
        org = self.context['request'].user
        job_title = JobTitle.objects.create(org = org, **validated_data)
        return job_title


class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ['founder', 'owner', 'title', 'description']

    def create(self, validated_data):
        user = self.context['user']
        org = Organization.objects.create(founder = user, owner = user, **validated_data)
        return org
    
class ProfileDetailSerializer(serializers.ModelSerializer):
    email = serializers.RelatedField(source = 'user.email', read_only = True)

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'middle_name', 'phone_number', 'profile_image', 'email', 'slug']

class OrderTitleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ['title', 'slug']

class EmployeeListSerializer(serializers.ModelSerializer):
    first_name = serializers.RelatedField(source = 'user.user.first_name', read_only = True)
    last_name = serializers.RelatedField(source = 'user.user.last_name', read_only = True)
    middle_name = serializers.RelatedField(source = 'user.user.middle_name', read_only = True)
    email = serializers.RelatedField(source = 'user.user.email', read_only = True)
    order = OrderTitleSerializer(many = True, read_only = True)
    job_title = serializers.RelatedField(source = 'job_title.title', read_only = True)

    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'middle_name', 'email',
                  'order', 'job_title','status']