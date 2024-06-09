from rest_framework import serializers

from .models import Vacancy, Resume, VacancyResponse
from authorization.models import Organization, UserProfile


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['title', 'slug']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['last_name', 'first_name', 'slug']


class VacancyResponseSerializer(serializers.ModelSerializer):
    applicant = UserProfileSerializer(read_only=True)

    class Meta:
        model = VacancyResponse
        fields = ['id', 'cover_letter', 'applicant']


class VacancyListSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    response_count = serializers.SerializerMethodField()

    class Meta:
        model = Vacancy
        fields = ['job_title', 'slug', 'min_salary', 'max_salary', 'currency',
                  'organization', 'location', 'experience', 'response_count']

    def __init__(self, *args, **kwargs):
        include_response_count = kwargs.pop('include_response_count', False)
        super().__init__(*args, **kwargs)
        if not include_response_count:
            self.fields.pop('response_count')

    def get_response_count(self, data):
        return VacancyResponse.objects.filter(vacancy=data).count()


class VacancyDetailSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = Vacancy
        fields = ['job_title', 'slug', 'min_salary', 'max_salary', 'currency', 'organization',
                  'location', 'experience', 'schedule', 'description', 'hide']

    def to_internal_value(self, data):
        if self.instance is None:
            self.fields['job_title'].required = True
        else:
            self.fields['job_title'].required = False
            self.fields['min_salary'].required = False
            self.fields['max_salary'].required = False
            self.fields['currency'].required = False
            self.fields['location'].required = False
            self.fields['experience'].required = False
            self.fields['schedule'].required = False
            self.fields['description'].required = False
            self.fields['hide'].required = False
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        instance.job_title = validated_data.pop('job_title', instance.job_title)
        instance.slug = validated_data.pop('slug', instance.slug)
        instance.min_salary = validated_data.pop('min_salary', instance.min_salary)
        instance.max_salary = validated_data.pop('max_salary', instance.max_salary)
        instance.currency = validated_data.pop('currency', instance.currency)
        instance.location = validated_data.pop('location', instance.location)
        instance.experience = validated_data.pop('experience', instance.experience)
        instance.schedule = validated_data.pop('schedule', instance.schedule)
        instance.description = validated_data.pop('description', instance.description)

        instance.save()
        return instance


class ResumeListSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Resume
        fields = ['job_title', 'slug', 'author', 'experience', 'updated_at']


class ResumeDetailSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Resume
        fields = ['job_title', 'slug', 'location', 'experience', 'author', 'schedule',
                  'min_salary', 'max_salary', 'currency', 'about_me', 'hide']

    def to_internal_value(self, data):
        if self.instance is None:
            self.fields['job_title'].required = True
        else:
            self.fields['job_title'].required = False
            self.fields['min_salary'].required = False
            self.fields['max_salary'].required = False
            self.fields['currency'].required = False
            self.fields['location'].required = False
            self.fields['experience'].required = False
            self.fields['schedule'].required = False
            self.fields['about_me'].required = False
            self.fields['hide'].required = False
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        instance.job_title = validated_data.pop('job_title', instance.job_title)
        instance.slug = validated_data.pop('slug', instance.slug)
        instance.min_salary = validated_data.pop('min_salary', instance.min_salary)
        instance.max_salary = validated_data.pop('max_salary', instance.max_salary)
        instance.currency = validated_data.pop('currency', instance.currency)
        instance.location = validated_data.pop('location', instance.location)
        instance.experience = validated_data.pop('experience', instance.experience)
        instance.schedule = validated_data.pop('schedule', instance.schedule)
        instance.about_me = validated_data.pop('about_me', instance.about_me)

        instance.save()
        return instance
