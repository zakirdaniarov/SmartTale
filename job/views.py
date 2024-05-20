from django.utils import timezone
from datetime import timedelta

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.db.models import Q

from authorization.models import Organization
from .models import Vacancy, Resume
from .serializers import (VacancyListSerializer, VacancyDetailSerializer,
                          ResumeListSerializer, ResumeDetailSerializer)
from .permissions import CurrentUserOrReadOnly
from .services import MyCustomPagination


class VacancyListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Список всех вакансий",
        operation_description="Этот эндпоинт предоставляет пользователю посмотреть все вакансии",
        responses={
            200: VacancyListSerializer,
            404: "Vacancy does not exist"
        },
        tags=["Vacancy"]
    )
    def get(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.all().order_by('-created_at')
        except Vacancy.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vacancy, request)
        if page is not None:
            serializer = VacancyListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = VacancyListSerializer(vacancy, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VacancyDetailAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Детальная страница вакансии",
        operation_description="Этот предостовляет пользователю просмотреть детальную страницу вакансии",
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

        serializer = VacancyDetailSerializer(vacancy)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddVacancyAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Добавление новой вакансии",
        operation_description="Этот предостовляет пользователю состоящий в организации добавить новую вакансию",
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

    @swagger_auto_schema(
        operation_summary="Изменение вакансии",
        operation_description="Этот эндпоинт предостовляет пользователю состоящий в организации изменять вакансию",
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
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        organization = Organization.objects.filter(owner=request.user.user_profile).first()

        if not organization:
            return Response({"error": "Only organization that added it can change"}, status=status.HTTP_403_FORBIDDEN)

        serializer = VacancyDetailSerializer(instance=vacancy, data=request.data)
        if serializer.is_valid():
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteVacancyAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Удаление вакансии",
        operation_description="Этот предостовляет пользователю удалить вакансию",
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
            400: "Bad Request",
            403: "Only organization that added it can delete",
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
        operation_description="Этот предостовляет пользователю найти нужную вакансию, "
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
            queryset = Vacancy.objects.filter(Q(job_title__istartswith=vacancy))
        else:
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vacancy, request)
        if page is not None:
            serializer = VacancyListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = VacancyListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VacancyFilterAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Фильтр вакансий",
        operation_description="Этот предостовляет пользователю отфилтровать вакансии "
                              "по должности, опыту работы, по локации, по валюте, по зарплате "
                              "за последние сутки, неделю, месяц, по организации",
        manual_parameters=[
            openapi.Parameter(
                "job_title",
                openapi.IN_QUERY,
                description="Фильтрация по должности",
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
                "location",
                openapi.IN_QUERY,
                description="Фильтрация по местоположении",
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
            openapi.Parameter(
                "currency",
                openapi.IN_QUERY,
                description="Фильтрация по валюте",
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
            200: "Created",
            403: "Only organization that added it can change",
            400: "Bad Request"
        },
        tags=["Vacancy"]
    )
    def get(self, request, *args, **kwargs):
        job_title = request.query_params.get('job_title', None)
        organization = request.query_params.get('organization', None)
        location = request.query_params.get('location', None)
        experience = request.query_params.get('experience', None)
        schedule = request.query_params.get('schedule', None)
        currency = request.query_params.get('currency', None)
        min_salary = request.query_params.get('min_salary', None)
        max_salary = request.query_params.get('max_salary', None)
        day = request.query_params.get('day', None)
        week = request.query_params.get('week', None)
        month = request.query_params.get('month', None)

        vacancy = Vacancy.objects.all().order_by('-created_at')

        if job_title:
            vacancy = vacancy.filter(job_title__icontains=job_title)
        if organization:
            vacancy = vacancy.filter(organization__title__icontains=organization)
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

        if not vacancy.exists():
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vacancy, request)
        if page is not None:
            serializer = VacancyListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = VacancyListSerializer(vacancy, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResumeListAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Список всех резюме",
        operation_description="Этот эндпоинт предоставляет пользователю посмотреть все резюме",
        responses={
            200: VacancyListSerializer,
            404: "Resume does not exist"
        },
        tags=["Resume"]
    )
    def get(self, request, *args, **kwargs):
        try:
            resume = Resume.objects.all().order_by('-created_at')
        except Resume.DoesNotExist:
            return Response({"error": "Resume does not exist"}, status=status.HTTP_404_NOT_FOUND)

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
        operation_description="Этот предостовляет пользователю просмотреть детальную страницу резюме",
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
        operation_description="Этот предостовляет пользователю добавить свое резюме",
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
        operation_description="Этот эндпоинт предостовляет пользователю изменять свое резюме",
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
        operation_description="Этот предостовляет пользователю удалить свое резюме",
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


class SearchResumeAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Поиск резюме",
        operation_description="Этот предостовляет пользователю найти нужное резюме, "
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
            resume_queryset = Resume.objects.filter(Q(job_title__istartswith=resume))
        else:
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(resume, request)
        if page is not None:
            serializer = ResumeListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ResumeListSerializer(resume_queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResumeFilterAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    pagination_class = MyCustomPagination

    @swagger_auto_schema(
        operation_summary="Фильтр резюме",
        operation_description="Этот предостовляет пользователю отфильтровать резюме "
                              "по должности, опыту работы, по локации, по графику работы",
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
            200: ResumeListSerializer,
            404: "Nothing was found for your request",
        },
        tags=["Resume"]
    )
    def get(self, request, *args, **kwargs):
        job_title = request.query_params.get('job_title', None)
        experience = request.query_params.get('experience', None)
        location = request.query_params.get('location', None)
        schedule = request.query_params.get('schedule', None)

        resume = Resume.objects.all().order_by('-created_at')

        if job_title:
            resume = resume.filter(job_title__icontains=job_title)
        if experience:
            resume = resume.filter(experience__icontains=experience)
        if location:
            resume = resume.filter(location__icontains=location)
        if schedule:
            resume = resume.filter(schedule__icontains=schedule)

        if not resume.exists():
            return Response({"error": "Nothing was found for your request"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(resume, request)
        if page is not None:
            serializer = ResumeListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ResumeListSerializer(resume, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
