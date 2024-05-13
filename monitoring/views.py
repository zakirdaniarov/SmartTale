import datetime as dt

from rest_framework.views import status, Response, APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from authorization.models import Organization

from .serializers import (JobTitleSeriailizer, OrganizationSerializer, ProfileDetailSerializer,
                          EmployeeListSerializer, JobTitleSerializer, EmployeeDetailSerializer)
from .models import Employee, JobTitle
from authorization.models import UserProfile

class UserDetailAPIView(APIView):
    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Подробная информация о юзере в маркетплейсе.",
        operation_description = "Предоставляет доступ к подробной информации юзера по slug в маркетплейсе.",
        responses = {
            200: ProfileDetailSerializer,
            404: "Not found",
        }
    )
    def get(self, request, userprofile_slug, *args, **kwargs):
        try:
            user = UserProfile.objects.get(slug = userprofile_slug)
        except Exception:
            return Response({"Error": "Пользователь не найден."}, status = status.HTTP_404_NOT_FOUND)
        serializer = ProfileDetailSerializer(user)
        return Response(serializer.data, status = status.HTTP_200_OK)

class OrganizationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Создание организации.",
        operation_description = "Предоставляет доступ к создани организации",
        responses = {
            201: OrganizationSerializer,
            400: "Invalid",
            403: "No permission"
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        if user.user_profile.sub_type == 'Нет подписки':
            return Response({"Error": "У Вас нет прав для создания организации!"}, status = status.HTTP_403_FORBIDDEN)
        if user.user_profile.sub_type == 'Премиум':
            if Organization.objects.filter(owner = user.user_profile).count() == 5:
                return Response({"Error": "Достигнут лимит по созданию организации (5)!"}, status = status.HTTP_400_BAD_REQUEST)
        else:
            if user.user_profile.subscription < dt.datetime.now(dt.timezone.utc):
                return Response({"Error": "Ваша подписка истекла!"}, status = status.HTTP_400_BAD_REQUEST)
        serializer = OrganizationSerializer(data = request.data, context = {'user': user.user_profile})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
class CreateJobTitleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Подробная информация о юзере в маркетплейсе.",
        operation_description = "Предоставляет доступ к подробной информации юзера по slug в маркетплейсе.",
        responses = {
            200: ProfileDetailSerializer,
            404: "Not found",
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        try:
            employee = Employee.objects.get(user = user.user_profile)
            if not employee.job_title:
                raise Exception("No permission")
            elif not employee.job_title.flag_create_jobtitle:
                raise Exception("No permission")
        except Exception:
            return Response({"Error": "У Вас нет прав на создание должностей!"}, status = status.HTTP_403_FORBIDDEN)
        serializer = JobTitleSeriailizer(data = request.data, context = {'org': employee.org})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeleteJobTitleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Подробная информация о юзере в маркетплейсе.",
        operation_description = "Предоставляет доступ к подробной информации юзера по slug в маркетплейсе.",
        responses = {
            200: ProfileDetailSerializer,
            404: "Not found",
        }
    )
    def delete(self, request, *args, **kwargs):
        user = request.user
        try:
            employee = Employee.objects.get(user = user.user_profile)
            if not employee.job_title:
                raise Exception("No permission")
            elif not employee.job_title.flag_delete_jobtitle:
                raise Exception("No permission")
        except Exception:
            return Response({"Error": "У Вас нет прав на удаление должностей!"}, status = status.HTTP_403_FORBIDDEN)
        job_title = JobTitle.objects.get(org = employee.org, title = request.data['title'])
        job_title.delete()
        return Response({"Success": "Job title has been deleted!"}, status = status.HTTP_200_OK)
    
class EmployeeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Список сотрудников текущей организации.",
        operation_description = "Предоставляет доступ к списку сотрудников текущей организации.",
        responses = {
            200: EmployeeListSerializer,
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        employees = Employee.objects.filter(org = user.user_profile.working_org.org)
        serializer = EmployeeListSerializer(employees, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
class EmployeeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["User"],
        operation_summary = "Подробная информация о юзере в организации.",
        operation_description = "Предоставляет доступ к подробной информации юзера по slug в организации.",
        responses = {
            200: EmployeeDetailSerializer,
            404: "Not found",
        }
    )
    def get(self, request, employee_slug, *args, **kwargs):
        try:
            user = UserProfile.objects.get(slug = employee_slug)
        except Exception:
            return Response({"Error.": "Пользователь не найден."}, status = status.HTTP_404_NOT_FOUND)
        try:
            user = Employee.objects.get(user = user)
        except Exception:
            return Response({"Error.": "Пользователь не является сотрудником какой-либо компании."}, status = status.HTTP_404_NOT_FOUND)
        serializer = EmployeeDetailSerializer(user)
        return Response(serializer.data, status = status.HTTP_200_OK)

def sort_for_jobs(item):
    result = 0
    result += item.flag_create_jobtitle
    result += item.flag_remove_jobtitle
    result += item.flag_update_access
    result += item.flag_add_employee
    result += item.flag_update_order
    result += item.flag_delete_order
    result += item.flag_remove_employee
    return result
              

class JobTitleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["User"],
        operation_summary = "Список должностей в текущей организации.",
        operation_description = "Предоставляет доступ к подробной списку должностей текущей организации отсортированный по количесту прав.",
        responses = {
            200: JobTitleSeriailizer,
            404: "Not found",
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        org = user.user_profile.working_org.org
        jobs = JobTitle.objects.filter(org = org)
        jobs = sorted(jobs, key = lambda item: sort_for_jobs(item), reverse = True)
        serializer = JobTitleSerializer(jobs, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
