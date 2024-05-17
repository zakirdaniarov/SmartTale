from rest_framework import views, status, permissions
from rest_framework.response import Response

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


class VacancyFilterAPIView(views.APIView):
    ...


class VacancySearchAPIView(views.APIView):
    def get(self, request, *args, **kwargs):
        try:
            vacancy = request.query_params.get('job_title', None)
            if vacancy:
                queryset = Vacancy.objects.filter(job_title__icontains=vacancy)
            else:
                queryset = Vacancy.objects.all()
        except:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = VacancyListSerializer(queryset, many=True)
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
