from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.db.models import Q

from authorization.models import Organization, UserProfile
from monitoring.models import STATUS_CHOICES
from monitoring.models import Employee
from .models import Vacancy, Resume, VacancyResponse
from .serializers import (VacancyListSerializer, VacancyDetailSerializer,
                          ResumeListSerializer, ResumeDetailSerializer, VacancyResponseSerializer)
from .permissions import CurrentUserOrReadOnly, AddVacancyEmployee, IsOrganizationEmployeeReadOnly
from .services import MyCustomPagination
from .firebase_config import send_fcm_notification


class VacancyListAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Список всех вакансий",
        operation_description="Этот эндпоинт предоставляет пользователю возможность посмотреть все вакансии,"
                              "а также отфильтровать вакансии "
                              "по должности, опыту работы, по локации, по зарплате "
                              "за последние сутки, неделю, месяц, по организации",
        manual_parameters=[
            openapi.Parameter(
                "params",
                openapi.IN_QUERY,
                description="Фильтрация по должности, по местоположении, по графику работы",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "organization__title",
                openapi.IN_QUERY,
                description="Фильтрация по организации",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "experience",
                openapi.IN_QUERY,
                description="Фильтрация по опыту работы",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "min_salary",
                openapi.IN_QUERY,
                description="Фильтрация по зарплате (по возрастанию)",
                type=openapi.TYPE_NUMBER,
                required=False,
            ),
            openapi.Parameter(
                "max_salary",
                openapi.IN_QUERY,
                description="Фильтрация по зарплате (по убыванию)",
                type=openapi.TYPE_NUMBER,
                required=False,
            ),
            openapi.Parameter(
                "days",
                openapi.IN_QUERY,
                description="Фильтрация по дням",
                type=openapi.TYPE_NUMBER,
                required=False,
            ),
            openapi.Parameter(
                "week",
                openapi.IN_QUERY,
                description="Фильтрация по неделе",
                type=openapi.TYPE_NUMBER,
                required=False,
            ),
            openapi.Parameter(
                "month",
                openapi.IN_QUERY,
                description="Фильтрация по месяцу",
                type=openapi.TYPE_NUMBER,
                required=False,
            ),
        ],
        responses={
            200: VacancyListSerializer,
            404: "Nothing was found for your request"
        },
        tags=["Vacancy"]
    )
    def get(self, request, *args, **kwargs):
        # params = request.query_params.get('params', '').split(',')
        params = dict(request.GET)
        for param in params:
            params[param] = params[param][0].split(',')
        all_job_titles = list(Vacancy.objects.values_list('job_title', flat=True).distinct())
        all_locations = list(Vacancy.objects.values_list('location', flat=True).distinct())
        all_schedules = list(Vacancy.objects.values_list('schedule', flat=True).distinct())
        print(params)
        job_title = [param for param in params.get('job_title', [])]
        location = [param for param in params.get('location', [])]
        schedule = [param for param in params.get('schedule', [])]
        organization = params.get('organization', None)
        experience = params.get('experience', None)
        min_salary = params.get('min_salary', None)
        min_salary = min_salary[0] if min_salary else None
        max_salary = params.get('max_salary', None)
        max_salary = max_salary[0] if max_salary else None
        day = params.get('day', None)
        week = params.get('week', None)
        month = params.get('month', None)

        try:
            vacancy = Vacancy.objects.all().order_by('-created_at')
        except Vacancy.DoesNotExist:
            return Response([], status=status.HTTP_404_NOT_FOUND)
        if job_title:
            vacancy = vacancy.filter(job_title__in=job_title)
        if organization:
            vacancy = vacancy.filter(organization__title__icontains=organization)
        if location:
            vacancy = vacancy.filter(location__in=location)
        if experience:
            vacancy = vacancy.filter(experience__icontains=experience)
        if schedule:
            vacancy = vacancy.filter(schedule__in=schedule)
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

        if not vacancy.exists():
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vacancy, request)
        if page is not None:
            serializer = VacancyListSerializer(page, many=True, include_response_count=False)
            return paginator.get_paginated_response(serializer.data)
        serializer = VacancyListSerializer(vacancy, many=True, include_response_count=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VacancyDetailAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Детальная страница вакансии",
        operation_description="Этот эндпоинт предостовляет пользователю возможность "
                              "просмотреть детальную страницу вакансии",
        responses={
            200: VacancyDetailSerializer,
            404: "Vacancy does not exist"
        },
        tags=['Vacancy']
    )
    def get(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Resume.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = VacancyDetailSerializer(vacancy, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddVacancyAPIView(views.APIView):
    permission_classes = [AddVacancyEmployee]

    @swagger_auto_schema(
        operation_summary="Добавление новой вакансии",
        operation_description="Этот эндпоинт предостовляет пользователю состоящий в организации "
                              "возможность добавить новую вакансию",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["job_title", "min_salary", "max_salary"],
            properties={
                "job_title": openapi.Schema(type=openapi.TYPE_STRING, description="Должность в вакансии"),
                "vacancy_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Слаг вакансии"),
                "experience": openapi.Schema(type=openapi.TYPE_STRING, description="Опыт работы"),
                "schedule": openapi.Schema(type=openapi.TYPE_STRING, description="График работы"),
                "location": openapi.Schema(type=openapi.TYPE_STRING, description="Место работы"),
                "min_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Минимальная зарплата"),
                "max_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Максимальная зарплата"),
                "currency": openapi.Schema(type=openapi.TYPE_STRING, description="Валюта зарплаты"),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Описание работы")
            },
        ),
        responses={
            201: VacancyDetailSerializer,
            403: "You must belong to an organization to create a vacancy",
            400: "Bad Request"
        },
        tags=["Vacancy"]
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        if Organization.objects.filter(founder=user.user_profile):
            organization = Organization.objects.filter(founder=user.user_profile, active=True).first()
        else:
            try:
                organization = user.user_profile.working_orgs.get().org()
            except Exception as e:
                return Response({"error": "You must belong to an organization to create a vacancy"},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = VacancyDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeVacancyAPIView(views.APIView):
    permission_classes = [AddVacancyEmployee]

    @swagger_auto_schema(
        operation_summary="Изменение вакансии",
        operation_description="Этот эндпоинт предостовляет возможность пользователю состоящий в организации, "
                              "и у которого есть права на добавление вакансии изменять вакансию",
        manual_parameters=[
            openapi.Parameter(
                "vacancy_slug",
                openapi.IN_PATH,
                description="Слаг вакансии",
                type=openapi.TYPE_STRING,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "job_title": openapi.Schema(type=openapi.TYPE_STRING, description="Должность в вакансии"),
                "vacancy_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Слаг вакансии"),
                "experience": openapi.Schema(type=openapi.TYPE_STRING, description="Опыт работы"),
                "schedule": openapi.Schema(type=openapi.TYPE_STRING, description="График работы"),
                "location": openapi.Schema(type=openapi.TYPE_STRING, description="Место работы"),
                "min_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Минимальная зарплата"),
                "max_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Максимальная зарплата"),
                "currency": openapi.Schema(type=openapi.TYPE_STRING, description="Валюта зарплаты"),
                "description": openapi.Schema(type=openapi.TYPE_STRING, description="Описание работы")
            },
        ),
        responses={
            201: VacancyDetailSerializer,
            400: "Bad Request",
            403: "Only organization that added it can change",
            404: "Vacancy does not exist"
        },
        tags=["Vacancy"]
    )
    def put(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Vacancy.DoesNotExist:
            return Response([])

        user = request.user.user_profile
        if Organization.objects.filter(founder=user):
            organization = Organization.objects.filter(founder=user, active=True).first()
        else:
            try:
                organization = user.working_orgs.get().org()
            except Exception as e:
                return Response({"error": "Only organization that added it can change"},
                                status=status.HTTP_400_BAD_REQUEST)

        serializer = VacancyDetailSerializer(instance=vacancy, data=request.data)
        if serializer.is_valid():
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteVacancyAPIView(views.APIView):
    permission_classes = [AddVacancyEmployee]

    @swagger_auto_schema(
        operation_summary="Удаление вакансии",
        operation_description="Этот эндпоинт предостовляет возможность пользователю удалить вакансию",
        manual_parameters=[
            openapi.Parameter(
                "vacancy_slug",
                openapi.IN_PATH,
                description="Слаг вакансии",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "vacancy_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Слаг вакансии"),
            },
        ),
        responses={
            200: "Successfully deleted",
            400: "Only organization that added it can delete",
            404: "Vacancy does not exist"
        },
        tags=["Vacancy"]
    )
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
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Поиск вакансий",
        operation_description="Этот эндпоинт предостовляет пользователю возможность найти нужную вакансию, "
                              "можно ввести только первую букву и выводится вакансии которые начинаются на эту букву",
        manual_parameters=[
            openapi.Parameter(
                "job_title",
                openapi.IN_QUERY,
                description="Поиск по должности",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={
            200: VacancyListSerializer,
            403: "Nothing was found for your request",
        },
        tags=["Vacancy"]
    )
    def get(self, request, *args, **kwargs):
        vacancy = request.query_params.get('job_title', None)

        if vacancy:
            queryset = Vacancy.objects.filter(Q(job_title__istartswith=vacancy)).order_by('-created_at')
        else:
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vacancy, request)
        if page is not None:
            serializer = VacancyListSerializer(page, many=True, include_response_count=False)
            return paginator.get_paginated_response(serializer.data)

        serializer = VacancyListSerializer(queryset, many=True, include_response_count=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VacancyByOrgAPIView(views.APIView):
    permission_classes = [ IsOrganizationEmployeeReadOnly]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Вакансии организации",
        operation_description="Этот эндпоинт предостовляет организации возможность вывести свои вакансии",
        responses={
            200: VacancyListSerializer,
            404: "Vacancy does not exist",
        },
        tags=["Vacancy"]
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
        vacancy = Vacancy.objects.filter(organization=employee.org).order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vacancy, request)
        if page is not None:
            serializer = VacancyListSerializer(vacancy, many=True, include_response_count=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = VacancyListSerializer(vacancy, many=True, include_response_count=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VacancyResponseListAPIView(views.APIView):
    permission_classes = [IsOrganizationEmployeeReadOnly]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Отклики вакансии",
        operation_description="Этот эндпоинт предостовляет организации "
                              "возможность вывести отклики определенной вакансии",
        responses={
            200: VacancyResponseSerializer,
            404: "No responses found for the given vacancy",
        },
        tags=["Vacancy"]
    )
    def get(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Vacancy.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if vacancy is not None:
            vacancy_response = VacancyResponse.objects.filter(vacancy=vacancy).order_by('-created_at')
        if not vacancy_response.exists():
            return Response({"error": "No responses found for the given vacancy"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vacancy_response, request)
        if page is not None:
            serializer = VacancyResponseSerializer(vacancy_response, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = VacancyResponseSerializer(vacancy_response, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VacancyResponseByUserAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Вывод вакансии на которые откликнулся",
        operation_description="Этот эндпоинт предостовляет пользователю "
                              "возможность вывести вакансии на которые откликнулся",
        responses={
            200: VacancyListSerializer,
            404: "Vacancy does not exist",
        },
        tags=["Vacancy"]
    )
    def get(self, request, *args, **kwargs):
        user_profile = request.user.user_profile
        applied_vacancy_responses = VacancyResponse.objects.filter(applicant=user_profile).values_list('vacancy__slug', flat=True)
        applied_vacancy = Vacancy.objects.filter(slug__in=applied_vacancy_responses).order_by('-created_at')

        try:
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(applied_vacancy, request)
            if page is not None:
                serializer = VacancyListSerializer(applied_vacancy, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = VacancyListSerializer(applied_vacancy, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)


class AddVacancyResponseAPIVIew(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Отклик на вакансию",
        operation_description="Этот эндпоинт предостовляет пользователю возможность "
                              "откликнутся на определенную вакансию",
        responses={
            200: VacancyResponseSerializer,
            404: "Vacancy does not exist",
            400: "Bad request"
        },
        tags=["Vacancy"]
    )
    def post(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Vacancy.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        try:
            applicant = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

        organization = vacancy.organization

        if organization.founder == applicant or organization.owner == applicant:
            return Response({"error": "You can't respond to vacancies posted by your own organization"},
                            status=status.HTTP_400_BAD_REQUEST)

        if Employee.objects.filter(user=applicant, org=organization).exists():
            return Response({"error": "You can't respond to vacancies posted by your own organization"},
                            status=status.HTTP_400_BAD_REQUEST)

        if VacancyResponse.objects.filter(vacancy=vacancy, applicant=applicant).exists():
            return Response({"error": "You have already applied for this vacancy"},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = VacancyResponseSerializer(data=request.data)
        if serializer.is_valid():
            applicant = request.user.user_profile
            serializer.save(vacancy=vacancy, applicant=applicant)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VacancyHideAPIView(views.APIView):
    permission_classes = [AddVacancyEmployee]

    @swagger_auto_schema(
        operation_summary="Скрыть вакансию",
        operation_description="Этот эндпоинт предостовляет органицазии возможность "
                              "скрывать свои вакансии",
        responses={
            200: "Vacancy hidden",
            400: "Only an employee of a certain position can hide a vacancy",
            404: "Vacancy does not exist",
        },
        tags=["Vacancy"]
    )
    def put(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Vacancy.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        current_organization = Organization.objects.filter(owner=request.user.user_profile).first()

        try:
            if vacancy.organization == current_organization:
                vacancy.hide = True if not vacancy.hide else False
                vacancy.save()
            else:
                return Response({"error": "Only an employee of a certain position can hide a vacancy"},
                        status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error when hiding vacancy: {e}"},
                            status=status.HTTP_400_BAD_REQUEST)

        if vacancy.hide:
            return Response({"data": "Vacancy hidden"}, status=status.HTTP_200_OK)
        else:
            return Response({"data": "Vacancy is not hidden"}, status=status.HTTP_200_OK)


class ResumeListAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Список всех резюме",
        operation_description="Этот эндпоинт предоставляет пользователю возможность посмотреть все резюме"
                              "а также отфильтровать резюме "
                              "по должности, опыту работы, "
                              "по локации, по графику работы",
        manual_parameters=[
            openapi.Parameter(
                "job_title",
                openapi.IN_QUERY,
                description="Фильтрация по должности",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "experience",
                openapi.IN_QUERY,
                description="Фильтрация по опыту работы",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "location",
                openapi.IN_QUERY,
                description="Фильтрация по местоположени",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "schedule",
                openapi.IN_QUERY,
                description="Фильтрация по графику работы",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={
            200: VacancyListSerializer,
            404: "Nothing was found for your request"
        },
        tags=["Resume"]
    )
    def get(self, request, *args, **kwargs):
        params = request.query_params.get('params', '').split(',')

        all_job_titles = list(Resume.objects.values_list('job_title', flat=True).distinct())
        all_locations = list(Resume.objects.values_list('location', flat=True).distinct())
        all_schedules = list(Resume.objects.values_list('schedule', flat=True).distinct())

        job_title = [param for param in params if param in all_job_titles]
        location = [param for param in params if param in all_locations]
        schedule = [param for param in params if param in all_schedules]

        experience = request.query_params.get('experience', None)

        try:
            resume = Resume.objects.all().order_by('-created_at')
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if job_title:
            resume = resume.filter(job_title__in=job_title)
        if experience:
            resume = resume.filter(experience__icontains=experience)
        if location:
            resume = resume.filter(location__in=location)
        if schedule:
            resume = resume.filter(schedule__in=schedule)

        if not resume.exists():
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(resume, request)
        if page is not None:
            serializer = ResumeListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ResumeListSerializer(resume, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResumeDetailAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Детальная страница резюме",
        operation_description="Этот эндпоинт предостовляет пользователю возможность "
                              "просмотреть детальную страницу резюме",
        responses={
            200: ResumeDetailSerializer,
            404: "Resume does not exist"
        },
        tags=['Resume']
    )
    def get(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.get(slug=kwargs['resume_slug'])
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResumeDetailSerializer(resume)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddResumeAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Добавление резюме",
        operation_description="Этот эндпоинт предостовляет пользователю возможность добавлять свои резюме",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["job_title"],
            properties={
                "job_title": openapi.Schema(type=openapi.TYPE_STRING, description="Должность в резюме"),
                "resume_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Слаг резюме"),
                "experience": openapi.Schema(type=openapi.TYPE_STRING, description="Опыт работы"),
                "schedule": openapi.Schema(type=openapi.TYPE_STRING, description="График работы"),
                "location": openapi.Schema(type=openapi.TYPE_STRING, description="Место работы"),
                "min_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Минимальная зарплата"),
                "max_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Максимальная зарплата"),
                "currency": openapi.Schema(type=openapi.TYPE_STRING, description="Валюта зарплаты"),
                "about_me": openapi.Schema(type=openapi.TYPE_STRING, description="Личная информация")
            },
        ),
        responses={
            201: VacancyDetailSerializer,
            400: "Bad Request"
        },
        tags=["Resume"]
    )
    def post(self, request, *args, **kwargs):
        serializer = ResumeDetailSerializer(data=request.data)
        if serializer.is_valid():
            author = request.user.user_profile
            serializer.save(author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeResumeAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Изменение резюме",
        operation_description="Этот эндпоинт предостовляет пользователю возможность возможность изменять свои резюме",
        manual_parameters=[
            openapi.Parameter(
                "resume_slug",
                openapi.IN_PATH,
                description="Слаг резюме",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "job_title": openapi.Schema(type=openapi.TYPE_STRING, description="Должность в резюме"),
                "resume_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Слаг резюме"),
                "experience": openapi.Schema(type=openapi.TYPE_STRING, description="Опыт работы"),
                "schedule": openapi.Schema(type=openapi.TYPE_STRING, description="График работы"),
                "location": openapi.Schema(type=openapi.TYPE_STRING, description="Место работы"),
                "min_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Минимальная зарплата"),
                "max_salary": openapi.Schema(type=openapi.TYPE_NUMBER, description="Максимальная зарплата"),
                "currency": openapi.Schema(type=openapi.TYPE_STRING, description="Валюта зарплаты"),
                "about_me": openapi.Schema(type=openapi.TYPE_STRING, description="Личная информация")
            },
        ),
        responses={
            201: VacancyDetailSerializer,
            400: "Bad Request",
            403: "Only author can change",
            404: "Resume does not exist"
        },
        tags=["Resume"]
    )
    def put(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.get(slug=kwargs['resume_slug'])
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ResumeDetailSerializer(instance=resume, data=request.data)
        if serializer.is_valid():
            author = request.user.user_profile

            if resume.author != author:
                return Response({"error": "Only author can change"}, status=status.HTTP_403_FORBIDDEN)

            serializer.save(author=author)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteResumeAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Удаление резюме",
        operation_description="Этот эндпоинт предостовляет пользователю возможность удалять свои резюме",
        manual_parameters=[
            openapi.Parameter(
                "resume_slug",
                openapi.IN_PATH,
                description="Слаг резюме",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "resume_slug": openapi.Schema(type=openapi.TYPE_STRING, description="Слаг резюме"),
            },
        ),
        responses={
            200: "Successfully deleted",
            403: "Only author can delete",
            404: "Resume does not exist"
        },
        tags=["Resume"]
    )
    def post(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.get(slug=kwargs['resume_slug'])
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)

        author = request.user.user_profile

        if resume.author == author:
            resume.delete()
        else:
            return Response({"error": "Only author can delete"}, status=status.HTTP_403_FORBIDDEN)
        return Response({"error": "Successfully deleted"}, status=status.HTTP_200_OK)


class ResumeByAuthorAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Свои резюме",
        operation_description="Этот эндпоинт предостовляет автору возможность "
                              "посмотреть свои резюме",
        responses={
            200: ResumeListSerializer,
            404: "You don't have a resume",
        },
        tags=["Resume"]
    )
    def get(self, request, *args, **kwargs):
        author = request.user.user_profile
        my_resume = author.author_resume.all().order_by('-created_at')

        if my_resume is None:
            return Response({"error": "You don't have a resume"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(my_resume, request)
        if page is not None:
            serializer = ResumeListSerializer(my_resume, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ResumeListSerializer(my_resume, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResumeHideAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Скрыть резюме",
        operation_description="Этот эндпоинт предостовляет автору возможность "
                              "скрывать свои резюме",
        responses={
            200: ResumeListSerializer,
            404: "Resume does not exist",
        },
        tags=["Resume"]
    )
    def put(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.get(slug=kwargs['resume_slug'])
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)

        try:
            if resume.author == request.user.user_profile:
                resume.hide = True if not resume.hide else False
                resume.save()
            else:
                return Response({"error": "Only the author can hide the resume"},
                        status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Error when hiding resume"},
                            status=status.HTTP_400_BAD_REQUEST)

        if resume.hide:
            return Response({"data": "Resume hidden"}, status=status.HTTP_200_OK)
        else:
            return Response({"data": "Resume is not hidden"}, status=status.HTTP_200_OK)


class SearchResumeAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Поиск резюме",
        operation_description="Этот эндпоинт предостовляет пользователю возможность найти нужное резюме, "
                              "можно ввести только первую букву и выводится резюме которые начинаются на эту букву",
        manual_parameters=[
            openapi.Parameter(
                "job_title",
                openapi.IN_QUERY,
                description="Поиск по должности",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={
            200: ResumeListSerializer,
            404: "Nothing was found for your request",
        },
        tags=["Resume"]
    )
    def get(self, request, *args, **kwargs):
        resume = request.query_params.get('job_title', None)

        if resume:
            resume_queryset = Resume.objects.filter(Q(job_title__istartswith=resume)).order_by('-created_at')
        else:
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(resume, request)
        if page is not None:
            serializer = ResumeListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ResumeListSerializer(resume_queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
