from rest_framework import serializers

from .models import Vacancy, Resume
from authorization.models import Organization, UserProfile


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['title']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['last_name', 'first_name', 'middle_name']


class VacancySerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = Vacancy
        fields = ['job_title', 'slug', 'location', 'experience', 'organization',
                  'description', 'schedule', 'min_salary', 'max_salary', 'currency']


class ResumeSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Resume
        fields = ['job_title', 'slug', 'location', 'experience', 'author', 'about_me',
                  'schedule', 'stack', 'min_salary', 'max_salary', 'currency']
