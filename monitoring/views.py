import datetime as dt
from operator import attrgetter

from django.db.models import Q
from rest_framework.views import status, Response, APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from marketplace.services import get_order_or_equipment, get_paginated_data
from .serializers import (JobTitleSeriailizer, OrganizationMonitoringSerializer, ProfileDetailSerializer,
                          EmployeeListSerializer, JobTitleSerializer, EmployeeDetailSerializer,
                          OrganizationDetailSerializer, OrganizationListSerializer,
                          EmployeeCreateSerializer, EmployeeDeleteSerializer, SubscribeSerializer)
from .models import Employee, JobTitle
from marketplace.models import Order, Equipment, Service
from marketplace.serializers import OrderListAPI, MyAdsSerializer
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
            200: ProfileDetailSerializer,
            404: "Not found",
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
        return Response(serializer.data, status = status.HTTP_200_OK)

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
            serializer.save()
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
            200: OrganizationDetailSerializer
        },
    )
    def get(self, request, org_slug):
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            return Response({"Error": "Организация не найдена."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(org, context={'detail': True})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class OrganizationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ['Organization'],
        operation_summary = "Список организаций пользователя",
        operation_description = "Этот эндпоинт предоставляет доступ к списку организаций пользователя.",
        responses = {
            200: OrganizationDetailSerializer
        },
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        orgs = Organization.objects.filter(owner = user.user_profile)
        if not orgs:
            return Response({"Error": "You don't have organizations!"}, status = status.HTTP_404_NOT_FOUND)
        serializer = OrganizationListSerializer(orgs, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)

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
        tags = ["Organization"],
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
            200: EmployeeDetailSerializer,
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
        try:
            employee = Employee.objects.get(user = user.user_profile)
            if not employee.job_title:
                raise Exception("No permission")
            elif not employee.job_title.flag_add_employee:
                raise Exception("No permission")
        except Exception:
            return Response({"Error": "У Вас нет прав на добавление сотрудников!"}, status = status.HTTP_403_FORBIDDEN)
        email = request.data['email']
        org_title = request.data['org_title']
        job_title = request.data['job_title']
        try:
            target_user = User.objects.get(email = email)
            target_user = UserProfile.objects.get(user = target_user)
        except Exception:
            return Response({"Error": "Нет существует такого пользователя!"}, status = status.HTTP_404_NOT_FOUND)
        try:
            org = Organization.objects.get(title = org_title)
        except Exception:
            return Response({"Error": "Нет существует такой организации!"}, status = status.HTTP_404_NOT_FOUND)
        try:
            job = JobTitle.objects.get(org = org, job_title = job_title)
        except Exception:
            return Response({"Error": "Нет существует такой должности!"}, status = status.HTTP_404_NOT_FOUND)
        Employee.objects.create(user = target_user, org = org, job_title = job)
        return Response({"Success": "Сотрудник добавлен"}, status = status.HTTP_201_CREATED)

class EmployeeDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

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
    def delete(self, request, *args, **kwargs):
        user = request.user
        try:
            employee = Employee.objects.get(user = user.user_profile)
            if not employee.job_title:
                raise Exception("No permission")
            elif not employee.job_title.flag_remove_employee:
                raise Exception("No permission")
        except Exception:
            return Response({"Error": "У Вас нет прав на добавление сотрудников!"}, status = status.HTTP_403_FORBIDDEN)
        user_slug = request.data['user_slug']
        try:
            target_user = UserProfile.objects.get(slug = user_slug)
        except Exception:
            return Response({"Error": "Нет такого пользователя."}, status = status.HTTP_404_NOT_FOUND)
        try:
            target_employee = Employee.objects.get(user = target_user)
        except Exception:
            return Response({"Error": "Нет такого сотрудника."}, status = status.HTTP_404_NOT_FOUND)
        if employee.working_org.org != target_employee.working_org.org:
            return Response({"Error": "Нельзя удалить сотрудника не из вашей организации."}, status = status.HTTP_403_FORBIDDEN)
        target_employee.delete()
        return Response({"Success": "Сотрудник успешно удален."}, status = status.HTTP_200_OK)

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
        tags = ["Organization"],
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

class SubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]


    @swagger_auto_schema(
        tags = ["User"],
        operation_summary = "Приобретение подписки.",
        operation_description = "Предоставляет возможность купить подписку.",
        manual_parameters=[
            openapi.Parameter(
                "subscription",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="Subscription type",
            ),
        ],
        responses = {
            200: SubscribeSerializer,
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
        

