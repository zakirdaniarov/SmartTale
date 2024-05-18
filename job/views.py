from django.utils import timezone
from datetime import timedelta
from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.db.models import Q
from django.db.models.functions import Lower
import django_filters

from authorization.models import Organization
from .models import Vacancy, Resume
from .serializers import (VacancyListSerializer, VacancyDetailSerializer,
                          ResumeListSerializer, ResumeDetailSerializer)
from .permissions import CurrentUserOrReadOnly
from .services import IsOrganizationFilter


class VacancyListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.all().order_by('-created_at')
        except Vacancy.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)
        serializer = VacancyListSerializer(vacancy, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddVacancyAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        organization = Organization.objects.filter(owner=request.user.user_profile).first()

        if not organization:
            return Response({"error": "You must belong to an organization to create a vacancy"},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = VacancyDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeVacancyAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def put(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Vacancy.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        organization = Organization.objects.filter(owner=request.user.user_profile).first()

        if not organization:
            return Response({"error": "Only organization that added it can change"}, status=status.HTTP_403_FORBIDDEN)

        serializer = VacancyDetailSerializer(instance=vacancy, data=request.data)
        if serializer.is_valid():
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteVacancyAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def post(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Vacancy.DoesNotExist:
            return Response({'error': "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        current_organization = Organization.objects.filter(owner=request.user.user_profile).first()

        if vacancy.organization == current_organization:
            vacancy.delete()
        else:
            return Response({"error": "Only organization that added it can delete"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Successfully deleted"}, status=status.HTTP_200_OK)


class VacancySearchAPIView(views.APIView):
    def get(self, request, *args, **kwargs):
        vacancy = request.query_params.get('job_title', None)

        if vacancy:
            queryset = Vacancy.objects.filter(Q(job_title__istartswith=vacancy))
        else:
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        serializer = VacancyListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VacancyFilterAPIView(views.APIView):
    def get(self, request, *args, **kwargs):
        location = request.query_params.get('location', None)
        experience = request.query_params.get('experience', None)
        schedule = request.query_params.get('schedule', None)
        job_title = request.query_params.get('job_title', None)
        currency = request.query_params.get('currency', None)
        min_salary = request.query_params.get('min_salary', None)
        max_salary = request.query_params.get('max_salary', None)
        day = request.query_params.get('day', None)
        week = request.query_params.get('week', None)
        month = request.query_params.get('month', None)

        vacancy = Vacancy.objects.all().order_by('-created_at')

        if job_title:
            vacancy = vacancy.filter(job_title__icontains=job_title)
        if location:
            vacancy = vacancy.filter(location__icontains=location)
        if experience:
            vacancy = vacancy.filter(experience__icontains=experience)
        if schedule:
            vacancy = vacancy.filter(schedule__icontains=schedule)

        # сортировка по зарплате

        if currency:
            vacancy = vacancy.filter(currency__icontains=currency)
            if min_salary:
                vacancy = vacancy.filter(min_salary__gte=min_salary)
            if max_salary:
                vacancy = vacancy.filter(max_salary__lte=max_salary)

        if day:
            day_ago = timezone.now() - timedelta(days=int(day))
            vacancy = vacancy.filter(created_at__gte=day_ago)

        if week:
            weeks_ago = timezone.now() - timedelta(weeks=int(week))
            vacancy = vacancy.filter(created_at__gte=weeks_ago)

        if month:
            month_ago = timezone.now() - timedelta(days=int(month) * 30)
            vacancy = vacancy.filter(created_at__gte=month_ago)

        serializer = VacancyListSerializer(vacancy, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResumeListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.all().order_by('-created_at')
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ResumeListSerializer(resume, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddResumeAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ResumeDetailSerializer(data=request.data)
        if serializer.is_valid():
            author = request.user.user_profile
            serializer.save(author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeResumeAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def put(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.get(slug=kwargs['resume_slug'])
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ResumeDetailSerializer(instance=resume, data=request.data)
        if serializer.is_valid():
            author = request.user.user_profile
            serializer.save(author=author)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteResumeAPIView(views.APIView):
    def post(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.get(slug=kwargs['resume_slug'])
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.user_profile

        if resume.author == author:
            resume.delete()
        else:
            return Response({"error": "Only author can delete"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Successfully deleted"}, status=status.HTTP_200_OK)


class SearchResumeAPIView(views.APIView):
    def get(self, request, *args, **kwargs):
        resume = request.query_params.get('job_title', None)

        if resume:
            resume_queryset = Resume.objects.filter(Q(job_title__istartswith=resume))
        else:
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResumeListSerializer(resume_queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
