import datetime as dt

from django.db.models.query import QuerySet
from rest_framework.views import status, Response, APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from .serializers import *
from .models import Employee, JobTitle
from authorization.models import UserProfile, User, Organization

SUBCRIPTION_CHOICES = (
    ('Тест-драйв', 'Тест-драйв'),
    ('Базовый', 'Базовый'),
    ('Премиум', 'Премиум'),
    ('Нет подписки', 'Нет подписки'),
)

class UserDetailAPIView(APIView):
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
        return Response(serializer.data, status = status.HTTP_200_OK)
    
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
                flag_remove_employee = True
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

class OrganizationActivateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ['Organization'],
        operation_summary = "Активировать организацию",
        operation_description = "Этот эндпоинт предоставляет возможность сделать организацию активной, а ту, что была активной деактивировать.",
        responses = {
            200: "Success"
        },
    )
    def put(self, request, org_slug, *args, **kwargs):
        user = request.user
        org = Organization.objects.filter(owner = user.user_profile, active = True).first()
        if not org:
            return Response({"Error": "You don't have organizations!"}, status = status.HTTP_404_NOT_FOUND)
        try:
            target_org = Organization.objects.get(owner = user.user_profile, slug = org_slug)
        except Exception:
            return Response({"Error": "Организация не найдена"}, status = status.HTTP_404_NOT_FOUND)
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
        if Organization.objects.filter(founder = user.user_profile):
            org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        else:
            employee = Employee.objects.filter(user = user.user_profile).first()
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
        if Organization.objects.filter(founder = user.user_profile):
            org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        else:
            employee = Employee.objects.filter(user = user.user_profile).first()
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
        if Organization.objects.filter(founder = user.user_profile):
            org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        else:
            employee = Employee.objects.filter(user = user.user_profile).first()
            if not employee or not employee.job_title or not employee.job_title.flag_update_access:
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
        if Organization.objects.filter(founder = user.user_profile):
            org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        else:
            employee = Employee.objects.filter(user = user.user_profile).first()
            if not employee or not employee.job_title or not employee.job_title.flag_remove_jobtitle:
                return Response({"Error": "У Вас нет прав на удаление должностей!"}, status = status.HTTP_403_FORBIDDEN)
            org = employee.org   
        try:
            job_title = JobTitle.objects.get(slug = jt_slug)
        except Exception:
            return Response({"Error": "Нет такой должности"}, status = status.HTTP_404_NOT_FOUND)
        if job_title.org != org:
            return Response({"Error": "Нельзя изменять должности не из своей активной организации"}, status = status.HTTP_404_NOT_FOUND)
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
    return result

class JobTitleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ["Organization"],
        operation_summary = "Список должностей в текущей организации.",
        operation_description = "Предоставляет доступ к подробной списку должностей текущей организации отсортированный по количесту прав.",
        responses = {
            200: JobTitleSerializer,
            404: "Not found",
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        if Organization.objects.filter(founder = user.user_profile):
            org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        else:
            try:
                org = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)
        jobs = JobTitle.objects.filter(org = org)
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
        if Organization.objects.filter(founder = user.user_profile):
            org = Organization.objects.filter(founder = user.user_profile, active = True).first()
        else:
            try:
                org = user.user_profile.working_orgs.get().org
            except Exception:
                return Response({"Error": "Вы не ещё не состоите ни в одной компании."}, status = status.HTTP_403_FORBIDDEN)
        employees = Employee.objects.filter(org = org)
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
            return Response({"Error.": "Вы не являетесь сотрудником какой-либо компании."}, status = status.HTTP_403_FORBIDDEN)
        serializer = EmployeeDetailSerializer(user)
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
        cur_org = Organization.objects.filter(founder = user.user_profile).exists()
        if not cur_org:
            employee = Employee.objects.filter(user = user.user_profile).first()
            if not employee or not employee.job_title or not employee.job_title.flag_remove_employee:
                return Response({"Error": "У Вас нет прав на удаление сотрудников!"}, status = status.HTTP_403_FORBIDDEN)
            cur_org = employee.org
        try:
            target_user = UserProfile.objects.get(slug = employee_slug)
        except Exception:
            return Response({"Error": "Нет такого пользователя."}, status = status.HTTP_404_NOT_FOUND)
        try:
            target_employee = Employee.objects.get(user = target_user)
        except Exception:
            return Response({"Error": "Нет такого сотрудника."}, status = status.HTTP_404_NOT_FOUND)
        if cur_org == False and cur_org != target_employee.working_orgs.get().org:
            return Response({"Error": "Нельзя удалить сотрудника не из вашей организации."}, status = status.HTTP_403_FORBIDDEN)
        target_employee.delete()
        return Response({"Success": "Сотрудник успешно удален."}, status = status.HTTP_200_OK)
    
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
        cur_org = Organization.objects.filter(founder = user.user_profile).exists()
        if not cur_org:
            employee = Employee.objects.filter(user = user.user_profile).first()
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
        if Employee.objects.filter(user = target_user).first():
            return Response({"Error": "Пользователь уже состоит в организации!"}, status = status.HTTP_400_BAD_REQUEST)
        try:
            org = Organization.objects.get(slug = org_slug)
        except Exception:
            return Response({"Error": "Нет существует такой организации!"}, status = status.HTTP_404_NOT_FOUND)
        if cur_org == False and org != cur_org:
            return Response({"Error": "Нельзя добавлять сотрудника не в свою организацию!"}, status = status.HTTP_400_BAD_REQUEST)
        try:
            job = JobTitle.objects.get(slug = jt_slug)
        except Exception:
            return Response({"Error": "Нет существует такой должности!"}, status = status.HTTP_404_NOT_FOUND)
        Employee.objects.create(user = target_user, org = org, job_title = job)
        return Response({"Success": "Сотрудник добавлен"}, status = status.HTTP_201_CREATED)

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
        

        