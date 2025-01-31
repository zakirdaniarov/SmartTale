import datetime as dt
import json
from operator import attrgetter

from django.db.models import Q

from drf_yasg import openapi
from rest_framework.views import status, Response, APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from drf_yasg.utils import swagger_auto_schema

from marketplace.services import get_order_or_equipment, get_paginated_data

from .serializers import *
from .models import Employee, JobTitle
from .models import STATUS_CHOICES
from marketplace.models import Order, Equipment, Service
from marketplace.serializers import OrderListAPI
from authorization.models import UserProfile, User, Organization

SUBCRIPTION_CHOICES = (
    ('Тест-драйв', 'Тест-драйв'),
    ('Базовый', 'Базовый'),
    ('Премиум', 'Премиум'),
    ('Нет подписки', 'Нет подписки'),
)

class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        tags = ["User"],
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
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserAdsAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def filter_queryset_by_search(self, queryset):
        search_query = self.request.query_params.get('title', '')
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        return queryset

    def get_orders_and_equipments(self, author, ads=None):
        user = self.request.user
        if ads == 'order':
            if user.is_authenticated:
                queryset = Order.objects.filter(author=author).order_by('-created_at')
            else:
                queryset = []
        elif ads == 'equipment':
            queryset = Equipment.objects.filter(author=author).order_by('-created_at')
        elif ads == 'service':
            queryset = Service.objects.filter(author=author).order_by('-created_at')
        elif ads is None:
            queryset = list(Equipment.objects.filter(author=author)) + list(Service.objects.filter(author=author))
            if user.is_authenticated:
                queryset += list(Order.objects.filter(author=author))
            queryset = sorted(queryset, key=attrgetter('created_at'), reverse=True)
        else:
            queryset = []

        return queryset

    @swagger_auto_schema(
        tags = ["User"],
        operation_summary = "Detailed information about user in marketplace.",
        operation_description = "Detailed information about user in marketplace by slug of the user",
        manual_parameters=[
            openapi.Parameter(
                'title',
                openapi.IN_QUERY,
                description="Filter the results by title (case insensitive).",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'ads',
                openapi.IN_QUERY,
                description="Filter the results by the type of advertisement (order, equipment, service). If not provided, returns all.",
                type=openapi.TYPE_STRING,
                enum=['order', 'equipment', 'service'],
                required=False
            )
        ],
        responses = {
            200: "Orders, services, and equipments list",
            404: "Orders, services, or equipments do not exist",
            500: "Server error",
        }
    )
    def get(self, request, userprofile_slug, *args, **kwargs):
        ads = request.query_params.get('ads')
        try:
            user = UserProfile.objects.get(slug = userprofile_slug)
        except Exception:
            return Response({"Error": "Пользователь не найден."}, status = status.HTTP_404_NOT_FOUND)
        ads_queryset = self.get_orders_and_equipments(user, ads)
        ads_queryset = self.filter_queryset_by_search(ads_queryset)
        data = get_order_or_equipment(ads_queryset, request)
        return Response(data, status=status.HTTP_200_OK)


class MyProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        tags = ["User"],
        operation_summary = "Подробная информация о моем профиле.",
        operation_description = "Предоставляет доступ к подробной информации о себе.",
        responses = {
            200: ProfileDetailSerializer,
            404: "Not found",
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = ProfileDetailSerializer(user.user_profile)
        sub = user.user_profile.subscription
        sub_type = user.user_profile.sub_type
        is_sub = False
        if sub_type == SUBCRIPTION_CHOICES[2][0] or (sub and sub > dt.datetime.now(dt.timezone.utc)):
            is_sub = True
        empl = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0])
        emp_serializer = MyEmployeeSerializer(empl, many = True)
        active_emp = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        org = None
        if active_emp:
            org = active_emp.org
        
        org_serializer = MyOrganizationSerializer(org)
        data = {
            'profile': serializer.data,
            'subscription': sub,
            'is_subbed': is_sub,
            'job_titles': emp_serializer.data,
            'org': org_serializer.data,
        }
        return Response(data, status = status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags = ["User"],
        operation_summary = "Изменение данных пользователя.",
        operation_description = "Предоставляет доступ к редактированию данных пользователя.",
        request_body = ProfileChangeSerializer,
        responses = {
            200: ProfileChangeSerializer,
            400: "Invalid data.",
        }
    )
    def put(self, request, *args, **kwargs):
        user = request.user
        serializer = ProfileChangeSerializer(user.user_profile, data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_200_OK)
        return Response({"Error": "Указаные невалидные данные."}, status = status.HTTP_400_BAD_REQUEST)

class OrganizationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Создание организации.",
        operation_description = "Предоставляет доступ к создани организации",
        responses = {
            201: OrganizationMonitoringSerializer,
            400: "Invalid",
            403: "No permission"
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        if user.user_profile.sub_type == SUBCRIPTION_CHOICES[3][0]:
            return Response({"Error": "У Вас нет прав для создания организации!"}, status = status.HTTP_403_FORBIDDEN)
        if user.user_profile.sub_type == SUBCRIPTION_CHOICES[2][0]:
            if Organization.objects.filter(owner = user.user_profile).count() == 5:
                return Response({"Error": "Достигнут лимит по созданию организации по подписке '{}' (5)!".format(user.user_profile.sub_type)}, status = status.HTTP_400_BAD_REQUEST)
        else:
            if user.user_profile.subscription < dt.datetime.now(dt.timezone.utc):
                return Response({"Error": "Ваша подписка истекла!"}, status = status.HTTP_400_BAD_REQUEST)
            if Organization.objects.filter(owner = user.user_profile).count() == 1:
                return Response({"Error": "Достигнут лимит по созданию организации по подписке '{}' (1)!".format(user.user_profile.sub_type)}, status = status.HTTP_400_BAD_REQUEST)
        serializer = OrganizationMonitoringSerializer(data = request.data, context = {'user': user.user_profile})
        if serializer.is_valid():
            org = serializer.save()
            job_founder = JobTitle.objects.create(
                title = 'Основатель',
                org = org,
                description = 'Основатель компании',
                flag_create_jobtitle = True,
                flag_remove_jobtitle = True,
                flag_update_access = True,
                flag_add_employee = True,
                flag_update_order = True,
                flag_delete_order = True,
                flag_remove_employee = True,
                flag_employee_detail_access = True,
                flag_create_vacancy = True,
                flag_change_employee_job = True
            )
            Employee.objects.create(
                user = user.user_profile,
                org = org,
                job_title = job_founder
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrganizationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationDetailSerializer

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Подробная информация об организации",
        operation_description = "Этот эндпоинт предоставляет доступ к подробной информации об организации с помощью slug.",
        responses = {
            200: OrganizationDetailSerializer,
            404: "Not found."
        },
    )
    def get(self, request, org_slug):
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            return Response({"Error": "Организация не найдена."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(org)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Изменение информации об организации",
        operation_description = "Этот эндпоинт предоставляет доступ к изменении информации об организации с помощью slug.",
        request_body = OrganizationDetailSwaggerSerializer,
        responses = {
            200: OrganizationDetailSerializer,
            403: "You are not the owner",
            404: "Not found"
        },
    )
    def put(self, request, org_slug):
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            return Response({"Error": "Организация не найдена."}, status=status.HTTP_404_NOT_FOUND)
        user = request.user.user_profile
        if user != org.owner:
            return Response({"Error": "Вы не можете изменять организацию."}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(org, data = request.data)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response({"Error": "Bad data."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Удаление информации об организации",
        operation_description = "Этот эндпоинт предоставляет доступ к удалению организации с помощью slug.",
        responses = {
            200: "Success",
            403: "You are not the owner",
            404: "Not found"
        },
    )
    def delete(self, request, org_slug):
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            return Response({"Error": "Организация не найдена."}, status=status.HTTP_404_NOT_FOUND)
        user = request.user.user_profile
        if user != org.owner:
            return Response({"Error": "Вы не можете удалять организацию."}, status=status.HTTP_403_FORBIDDEN)
        flag = Employee.objects.get(user = user, org = org).active
        org.delete()
        employee = Employee.objects.filter(user = user).first()
        if employee:
            employee.active = True
        return Response({"Success": "Организация успешно удалена."}, status=status.HTTP_200_OK)
    
class OrganizationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ['Organization'],
        operation_summary = "Список организаций пользователя",
        operation_description = "Этот эндпоинт предоставляет доступ к списку организаций пользователя.",
        responses = {
            200: MyOrganizationListSerializer
        },
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0])
        org_ids = [item.org.id for item in employee]
        orgs = Organization.objects.filter(id__in = org_ids)
        # my_orgs = []
        # other_orgs = []
        # for item in employee:
        #     if item.org.owner != user.user_profile:
        #         other_orgs.append(item.org.pk)
        #     else:
        #         my_orgs.append(item.org.pk)
        # my_orgs = Organization.objects.filter(pk__in = my_orgs)
        # other_orgs = Organization.objects.filter(pk__in = other_orgs)
        serializer1 = MyOrganizationListSerializer(orgs, many = True)
        serializer2 = OrganizationActiveSerializer(employee, many = True)
        data = {
            'my_orgs': serializer1.data,
            'orgs_active': serializer2.data
        }
        return Response(data, status = status.HTTP_200_OK)

class OrganizationActivateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ['Organization'],
        operation_summary = "Активировать организацию",
        operation_description = "Этот эндпоинт предоставляет возможность сделать организацию активной, а ту, что была активной деактивировать.",
        responses = {
            200: "Success",
            404: "No such organization"
        },
    )
    def put(self, request, org_slug, *args, **kwargs):
        user = request.user
        # org = Organization.objects.filter(owner = user.user_profile, active = True).first()
        try:
            target_org = Organization.objects.get(slug = org_slug)
        except Exception:
            return Response({"Error": "No such organization!"}, status = status.HTTP_404_NOT_FOUND)
        try:
            target_org = Employee.objects.get(user = user.user_profile, status = STATUS_CHOICES[0][0], org = target_org)
        except Exception:
            return Response({"Error": "You aren't employee of this organization!"}, status = status.HTTP_404_NOT_FOUND)
        org = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if org:
            org.active = False
            org.save()
        target_org.active = True
        target_org.save()
        return Response({"Success": "Организация успешно активирована"}, status = status.HTTP_200_OK)

# Create your views here.
class CreateJobTitleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Создание должности.",
        operation_description = "Предоставляет возможность создания должности в организации.",
        responses = {
            200: JobTitleSerializer,
            400: "Invalid data",
            403: "No permission"
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        # if Organization.objects.filter(founder = user.user_profile):
        #     org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # else:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee or not employee.job_title or not employee.job_title.flag_create_jobtitle:
            return Response({"Error": "У Вас нет прав на создание должностей!"}, status = status.HTTP_403_FORBIDDEN)
        org = employee.org   
        if JobTitle.objects.filter(org = org, title = request.data['title']).first():
            return Response({"Error": "Должность с таким именем в организации уже существует!"}, status = status.HTTP_400_BAD_REQUEST)
        serializer = JobTitleSerializer(data = request.data, context = {'org': org})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class JobTitleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Подробная информация о должности в организации.",
        operation_description = "Предоставляет доступ к подробной информации о должности в организации.",
        responses = {
            200: JobTitleSerializer,
            403: "Forbidden",
            404: "Not found",
        }
    )
    def get(self, request, jt_slug, *args, **kwargs):
        user = request.user
        # if Organization.objects.filter(founder = user.user_profile):
        #     org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # else:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee:
            return Response({"Error": "У Вас нет прав на просмотр должностей!"}, status = status.HTTP_403_FORBIDDEN)
        org = employee.org
        try:
            job_title = JobTitle.objects.get(slug = jt_slug)
        except Exception:
            return Response({"Error": "Нет такой должности"}, status = status.HTTP_404_NOT_FOUND)
        if job_title.org != org:
            return Response({"Error": "Нельзя просматривать должности не из своей активной организации"}, status = status.HTTP_404_NOT_FOUND)
        serializer = JobTitleSerializer(job_title)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Изменение прав у должности.",
        operation_description = "Предоставляет доступ к изменению прав должности.",
        responses = {
            200: ProfileDetailSerializer,
            400: "Invalid data",
            403: "Forbidden",
            404: "Not found"
        }
    )
    def put(self, request, jt_slug, *args, **kwargs):
        user = request.user
        # if Organization.objects.filter(founder = user.user_profile):
        #     org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # else:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee or not employee.job_title or not employee.job_title.flag_create_jobtitle:
            return Response({"Error": "У Вас нет прав на изменение прав должностей!"}, status = status.HTTP_403_FORBIDDEN)
        org = employee.org     
        try:
            job_title = JobTitle.objects.get(slug = jt_slug)
        except Exception:
            return Response({"Error": "Нет такой должности"}, status = status.HTTP_404_NOT_FOUND)
        if job_title.org != org:
            return Response({"Error": "Нельзя изменять должности не из своей активной организации"}, status = status.HTTP_400_BAD_REQUEST)
        serializer = JobTitleSerializer(job_title, data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_200_OK)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Удаление должности.",
        operation_description = "Предоставляет возможность удаления должности с организации.",
        responses = {
            200: "Success",
            403: "No permission",
            404: "Not found"
        }
    )
    def delete(self, request, jt_slug, *args, **kwargs):
        user = request.user
        # if Organization.objects.filter(founder = user.user_profile):
        #     org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # else:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee or not employee.job_title or not employee.job_title.flag_remove_jobtitle:
            return Response({"Error": "У Вас нет прав на удаление должностей!"}, status = status.HTTP_403_FORBIDDEN)
        org = employee.org   
        try:
            job_title = JobTitle.objects.get(slug = jt_slug)
        except Exception:
            return Response({"Error": "Нет такой должности"}, status = status.HTTP_404_NOT_FOUND)
        if job_title.org != org:
            return Response({"Error": "Нельзя удалять должности не из своей активной организации"}, status = status.HTTP_404_NOT_FOUND)
        job_title.delete()
        return Response({"Success": "Job title has been deleted!"}, status = status.HTTP_200_OK)

def sort_for_jobs(item):
    result = 0
    result += item.flag_create_jobtitle
    result += item.flag_remove_jobtitle
    result += item.flag_update_access
    result += item.flag_add_employee
    result += item.flag_update_order
    result += item.flag_delete_order
    result += item.flag_remove_employee
    result += item.flag_change_employee_job
    result += item.flag_create_vacancy
    result += item.flag_employee_detail_access
    return result

class JobTitleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Список должностей в текущей организации.",
        operation_description = "Предоставляет доступ к подробному списку должностей текущей организации отсортированный по количесту прав.",
        responses = {
            200: JobTitleSerializer,
            404: "Not found",
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        # if Organization.objects.filter(founder = user.user_profile):
        #     org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # else:
        try:
            # org = user.user_profile.working_orgs.get().org
            employee = Employee.objects.get(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True)
        except Exception:
            return Response({"Error": "Вы не ещё не состоите ни в одной компании или не активирована ни одна из организаций."}, status = status.HTTP_403_FORBIDDEN)
        jobs = JobTitle.objects.filter(org = employee.org)
        jobs = sorted(jobs, key = lambda item: sort_for_jobs(item), reverse = True)
        serializer = JobTitleSerializer(jobs, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
     
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
        # if Organization.objects.filter(founder = user.user_profile):
        #     org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # else:
        try:
            # org = user.user_profile.working_orgs.get().org
            employee = Employee.objects.get(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True)
        except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании или не активирована ни одна из организаций."}, status = status.HTTP_403_FORBIDDEN)
        employees = Employee.objects.filter(org = employee.org)
        serializer = EmployeeListSerializer(employees, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
class EmployeeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Подробная информация о юзере в организации.",
        operation_description = "Предоставляет доступ к подробной информации юзера по slug в организации.",
        responses = {
            200: EmployeeDetailSerializer,
            404: "Not found",
        }
    )
    def get(self, request, employee_slug, *args, **kwargs):
        user = request.user
        # cur_org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # if not cur_org:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee:
            return Response({"Error": "Вы не состоите ни в одной организации!"}, status = status.HTTP_403_FORBIDDEN)
        cur_org = employee.org
        try:
            target_user = UserProfile.objects.get(slug = employee_slug)
        except Exception:
            return Response({"Error.": "Пользователь не найден."}, status = status.HTTP_404_NOT_FOUND)
        target_user = Employee.objects.filter(user = target_user, org = cur_org).first()
        if not target_user:
            return Response({"Error.": "Нет такого сотрудника в Вашей активной организации"}, status = status.HTTP_403_FORBIDDEN)
        serializer = EmployeeDetailSerializer(target_user)
        return Response(serializer.data, status = status.HTTP_200_OK)

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Изменение должности сотрудника в организаци.",
        operation_description = "Предоставляет доступ к изменению должности пользователя в организации.",
        request_body = EmployeeChangeSerializer,
        responses = {
            200: EmployeeDetailSerializer,
            403: "No permission for changing job of employee",
            404: "No found",
        }
    )
    def put(self, request, employee_slug, *args, **kwargs):
        user = request.user
        # cur_org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # if not cur_org:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee or not employee.job_title or not employee.job_title.flag_change_employee_job:
            return Response({"Error": "У Вас нет прав на изменение сотрудников!"}, status = status.HTTP_403_FORBIDDEN)
        cur_org = employee.org
        jt_slug = request.data['jt_slug']
        try:
            target_user = UserProfile.objects.get(slug = employee_slug)
        except Exception:
            return Response({}, status = status.HTTP_200_OK)
        try:
            target_employee = Employee.objects.get(org = cur_org, user = target_user)
        except Exception:
            return Response({}, status = status.HTTP_200_OK)
        try:
            job = JobTitle.objects.get(slug = jt_slug)
        except:
            return Response({}, status = status.HTTP_200_OK)
        target_employee.job_title = job
        target_employee.save()
        serializer = EmployeeDetailSerializer(target_employee)
        return Response(serializer.data, status = status.HTTP_200_OK)

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Удаление сотрудника из организации.",
        operation_description = "Предоставляет доступ к удалению сотрудника из организации.",
        request_body = EmployeeDeleteSerializer,
        responses = {
            200: "User is deleted",
            403: "No permission for deletion",
            404: "Not user or employee",
        }
    )
    def delete(self, request, employee_slug, *args, **kwargs):
        user = request.user
        # cur_org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        # if not cur_org:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee or not employee.job_title or not employee.job_title.flag_remove_employee:
            return Response({"Error": "У Вас нет прав на удаление сотрудников!"}, status = status.HTTP_403_FORBIDDEN)
        cur_org = employee.org
        try:
            target_user = UserProfile.objects.get(slug = employee_slug)
        except Exception:
            return Response({"Error": "Нет такого пользователя."}, status = status.HTTP_404_NOT_FOUND)
        try:
            target_employee = Employee.objects.get(org = cur_org, user = target_user)
        except Exception:
            return Response({"Error": "Нет такого сотрудника в Вашей активной организации."}, status = status.HTTP_404_NOT_FOUND)
        target_employee.delete()
        return Response({"Success": "Сотрудник успешно удален."}, status = status.HTTP_200_OK)

class EmployeeOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def filter_queryset_by_search(self, queryset):
        search_query = self.request.query_params.get('title', '')
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query))
        return queryset

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Detailed information about employees orders.",
        operation_description = "Detailed information about employees orders by employees slug.",
        manual_parameters=[
            openapi.Parameter(
                "title",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Search query to filter orders by title (case-insensitive)",
            ),
            openapi.Parameter(
                "stage",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Shows in which stage is order, active or finished",
            )
        ],
        responses = {
            200: OrderListAPI,
            404: "Not found",
        }
    )
    def get(self, request, employee_slug, *args, **kwargs):
        stage = self.request.query_params.get('stage')
        try:
            user = UserProfile.objects.get(slug = employee_slug)
        except Exception:
            return Response({"Error.": "Пользователь не найден."}, status = status.HTTP_404_NOT_FOUND)
        try:
            user = Employee.objects.get(user = user)
        except Exception:
            return Response({"Error.": "Пользователь не является сотрудником какой-либо компании."}, status = status.HTTP_404_NOT_FOUND)
        if stage == 'active':
            orders = user.order.filter(is_finished=False).order_by('booked_at')
            list_type = "my-history-orders-active"
        elif stage == 'finished':
            orders = user.order.filter(is_finished=True).order_by('booked_at')
            list_type = "my-history-orders-finished"
        else:
            orders = user.order.all().order_by('booked_at')
            list_type = None
        order_queryset = self.filter_queryset_by_search(orders)
        paginated_data = get_paginated_data(order_queryset, request, list_type)
        return Response(paginated_data, status=status.HTTP_200_OK)


class OrderEmployeesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Order"],
        operation_summary="List employees for a specific order",
        operation_description="Get a list of employees working on a specific order by order slug.",
        manual_parameters=[
            openapi.Parameter(
                "order_slug",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="Slug of the order"
            )
        ],
        responses={
            200: openapi.Response(
                description="List of employees",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "user_profile": openapi.Schema(type=openapi.TYPE_STRING),
                            "job_title": openapi.Schema(type=openapi.TYPE_STRING),
                            "status": openapi.Schema(type=openapi.TYPE_STRING),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            ),
            404: "Not found",
        }
    )
    def get(self, request, order_slug, *args, **kwargs):
        try:
            order = Order.objects.get(slug=order_slug)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        employee = Employee.objects.filter(user=user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee:
            return Response({"Error": "Вы не состоите ни в одной организации!"}, status = status.HTTP_403_FORBIDDEN)
        cur_org = employee.org
        if cur_org != order.org_work:
            return Response({"Error": "You don't have access for this page"}, status = status.HTTP_403_FORBIDDEN)
        employees = order.workers.all()
        print("heallo")
        serializer = EmployeeListSerializer(employees, many = True)
        print("fdasfdsa")
        return Response(serializer.data, status=status.HTTP_200_OK)


class EmployeeCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Приглашение сотрудника в организаци.",
        operation_description = "Предоставляет доступ к добавлению пользователя в организацию.",
        request_body = EmployeeCreateSerializer,
        responses = {
            201: "Employee added to organization",
            403: "No permission for adding employee",
            404: "No such user",
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        # cur_org = Organization.objects.filter(founder = user.user_profile).exists()
        # if not cur_org:
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        if not employee or not employee.job_title or not employee.job_title.flag_add_employee:
            return Response({"Error": "У Вас нет прав на добавление сотрудников!"}, status = status.HTTP_403_FORBIDDEN)
        cur_org = employee.org
        email = request.data['email']
        org_slug = request.data['org_slug']
        jt_slug = request.data['jt_slug']
        try:
            target_user = User.objects.get(email = email)
            target_user = UserProfile.objects.get(user = target_user)
        except Exception:
            return Response({"Error": "Нет существует такого пользователя!"}, status = status.HTTP_404_NOT_FOUND)
        if Employee.objects.filter(user = target_user, status = STATUS_CHOICES[0][0]).first():
            return Response({"Error": "Пользователь уже состоит в организации!"}, status = status.HTTP_400_BAD_REQUEST)
        try:
            org = Organization.objects.get(slug = org_slug)
        except Exception:
            return Response({"Error": "Нет существует такой организации!"}, status = status.HTTP_404_NOT_FOUND)
        if Employee.objects.filter(user = target_user, org = org,status = STATUS_CHOICES[1][0]).first():
            return Response({"Error": "Пользователю уже была отправлена заявка!"}, status = status.HTTP_400_BAD_REQUEST)
        if cur_org == False and org != cur_org:
            return Response({"Error": "Нельзя добавлять сотрудника не в свою организацию!"}, status = status.HTTP_400_BAD_REQUEST)
        try:
            job = JobTitle.objects.get(slug = jt_slug)
        except Exception:
            return Response({"Error": "Нет существует такой должности!"}, status = status.HTTP_404_NOT_FOUND)
        Employee.objects.create(user = target_user, org = org, job_title = job, status = STATUS_CHOICES[1][0])
        return Response({"Success": "Приглашение отправлено"}, status = status.HTTP_201_CREATED)

class EmployeeApplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Принятие приглашения в организаци.",
        operation_description = "Предоставляет доступ к принятию приглашения в организацию.",
        request_body = EmployeeExitSerializer,
        responses = {
            200: "Success",
            400: "Bad data",
            404: "No such organization",
        }
    )
    def put(self, request, *args, **kwargs):
        user = request.user
        org_slug = request.data['org_slug']
        try:
            org = Organization.objects.get(slug = org_slug)
        except Exception:
            return Response({"Error": "Нет существует такой организации!"}, status = status.HTTP_404_NOT_FOUND)
        if Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0]).first():
            return Response({"Error": "Вы уже состоите в организации!"}, status = status.HTTP_400_BAD_REQUEST)
        employee = Employee.objects.filter(user = user.user_profile, org = org, status = STATUS_CHOICES[1][0]).first()
        if not employee:
            return Response({"Success": "Нет приглашения в данную организацию!"}, status = status.HTTP_400_BAD_REQUEST)
        employee.status = STATUS_CHOICES[0][0]
        employee.active = True
        employee.save()
        other_invites = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[1][0])
        if other_invites:
            other_invites.delete()
        return Response({"Success": "Вы успешно вступили в организацию!"}, status = status.HTTP_200_OK)

class EmployeeDeclineAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Отказ приглашения в организаци.",
        operation_description = "Предоставляет доступ к отказу приглашения в организацию.",
        request_body = EmployeeExitSerializer,
        responses = {
            200: "Success",
            400: "Bad data",
            404: "No such organization",
        }
    )
    def delete(self, request, *args, **kwargs):
        user = request.user
        org_slug = request.data['org_slug']
        try:
            org = Organization.objects.get(slug = org_slug)
        except Exception:
            return Response({"Error": "Нет существует такой организации!"}, status = status.HTTP_404_NOT_FOUND)
        employee = Employee.objects.filter(user = user.user_profile, org = org, status = STATUS_CHOICES[1][0]).first()
        if not employee:
            return Response({"Success": "Нет приглашения в данную организацию!"}, status = status.HTTP_400_BAD_REQUEST)
        employee.delete()
        return Response({"Success": "Вы отказались вступать в данную организацию!"}, status = status.HTTP_200_OK)

class OrgInvitesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Список приглашений в организации.",
        operation_description = "Предоставляет доступ к списку приглашений из организаций.",
        responses = {
            200: InvitesSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[1][0])
        serializer = InvitesSerializer(employee, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)



class EmployeeExitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Уход из организаци.",
        operation_description = "Предоставляет доступ к уходу пользователя из организации.",
        request_body = EmployeeExitSerializer,
        responses = {
            200: "Success",
            404: "No such org or employee",
        }
    )
    def delete(self, request, *args, **kwargs):
        user = request.user
        org_slug = request.data['org_slug']
        try:
            org = Organization.objects.get(slug = org_slug)
        except Exception:
            return Response({"Error": "Нет такой организации!"}, status = status.HTTP_404_NOT_FOUND)
        employee = Employee.objects.filter(user = user.user_profile, org = org, status = STATUS_CHOICES[0][0]).first()
        if not employee:
            return Response({"Error": "Вы не являетесь сотрудником этой организации!"}, status = status.HTTP_400_BAD_REQUEST)
        active = employee.active
        employee.delete()
        if active:
            new_active = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0]).first()
            if new_active:
                new_active.active = True
                new_active.save()
        return Response({"Success": "Вы успешнок покинули организацию!"}, status = status.HTTP_200_OK)


class SubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["User"],
        operation_summary = "Приобретение подписки.",
        operation_description = "Предоставляет возможность купить подписку.",
        request_body = SubscribeRequestSerializer,
        responses = {
            200: SubscribeResponseSerializer,
            400: "Invalid data",
        }
    )
    def put(self, request, *args, **kwargs):
        user = request.user
        sub = request.data['subscription']
        user_profile = UserProfile.objects.get(user = user)
        if sub == SUBCRIPTION_CHOICES[0][0]:
            if not user_profile.subscription or user_profile.subscription < dt.datetime.now(dt.timezone.utc):
                user_profile.subscription = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days = 7)
            else:
                user_profile.subscription = user_profile.subscription + dt.timedelta(days = 7)
        elif sub == SUBCRIPTION_CHOICES[1][0]:
            if not user_profile.subscription or user_profile.subscription < dt.datetime.now(dt.timezone.utc):
                user_profile.subscription = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days = 60)
            else:
                user_profile.subscription = user_profile.subscription + dt.timedelta(days = 60)
        elif sub == SUBCRIPTION_CHOICES[2][0]:
            pass
        else:
            return Response({"Error": "Нет существует такой подписки."}, status = status.HTTP_400_BAD_REQUEST)
        user_profile.sub_type = sub
        user_profile.save()
        return Response({"new_sub_dt": user_profile.subscription}, status = status.HTTP_200_OK)
        

