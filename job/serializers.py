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


class VacancyListSerializer(serializers.ModelSerializer):

    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = Vacancy
        fields = ['job_title', 'slug', 'min_salary', 'max_salary',
                  'currency', 'organization', 'location', 'experience']


class VacancyDetailSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = Vacancy
        fields = ['job_title', 'slug', 'min_salary', 'max_salary', 'currency',
                  'organization', 'location', 'experience', 'description', 'schedule']


class ResumeListSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Resume
        fields = ['job_title', 'slug', 'author', 'experience']


class ResumeDetailSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Resume
        fields = ['job_title', 'slug', 'location', 'experience', 'author', 'about_me',
                  'schedule', 'stack', 'min_salary', 'max_salary', 'currency']
