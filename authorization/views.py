import datetime as dt

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import Response, APIView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_yasg.utils import swagger_auto_schema

from .serializers import RegistrationSerializer, LoginSerializer
from .models import User, UserProfile, ConfirmationCode
from .services import get_tokens_for_user, create_token_and_send_to_email, destroy_token
from .swagger import (login_swagger, resend_swagger, verify_swagger, 
                      register_swagger, delete_swagger, logout_swagger)

class SignupAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags = ['Registration'],
        operation_description = "Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "зарегистрироваться в приложении "
                              "с помощью электронной почты.",
        request_body = register_swagger['request_body'],                      
        responses = {
            201: "Success.",
            400: "Invalid data.",
        },
    )
    def post(self, request):
        serializer = RegistrationSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        first_name = serializer.validated_data.pop('first_name')
        last_name = serializer.validated_data.pop('last_name')
        middle_name = serializer.validated_data.pop('middle_name')
        phone_number = serializer.validated_data.pop('phone_number')
        serializer.save()
        user = User.objects.get(email = serializer.validated_data['email'])
        try:
            UserProfile.objects.create(user = user, first_name = first_name, last_name = last_name, middle_name = middle_name,
                                       phone_number = phone_number)
        except Exception as e:
            user.delete()
            return Response({'Error': 'Невалидное имя, фамилия или отчество.'}, status = status.HTTP_400_BAD_REQUEST)
        create_token_and_send_to_email(user = user)
        return Response({"Success": "User is created."}, status = status.HTTP_201_CREATED)
    
class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags = ['Authorization'],
        operation_description = "Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "войти в приложении "
                              "с помощью электронной почты и пароля.",
        request_body = login_swagger['request_body'],                      
        responses = {
            200: login_swagger['response'],
            400: "Invalid data.",
            403: "Not verified.",
            404: "Not found.",
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = User.objects.filter(email = email).first()
        if user is None:
            return Response({"Error" : "Пользователя с заданным email не существует."}, status = status.HTTP_404_NOT_FOUND)
        if not user.is_verified:
            return Response({"Error" : "Пользователь ещё не верифицирован!"}, status = status.HTTP_403_FORBIDDEN)
        if not user.check_password(password):
            return Response({"Error": "Неправильный пароль!"}, status = status.HTTP_400_BAD_REQUEST)
        tokens = get_tokens_for_user(user)
        slug = user.user_profile.slug
        return_data = {
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'data': {'slug': slug},
        }
        return Response(return_data, status = status.HTTP_200_OK)
        

class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags = ['Registration'],
        operation_description = "Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "верифицировать аккаунт "
                              "с помощью кода, отправленного на почту.",
        request_body = verify_swagger['request_body'],                      
        responses = {
            200: "Success.",
            400: "Already verified or invalid/expired token.",
        },
    )
    def post(self, request):
        email = request.data['email']
        user = get_object_or_404(User, email = email)
        if user.is_verified == True:
            return Response({"Error": "Пользователь уже верифицирован"}, status = status.HTTP_400_BAD_REQUEST)
        code = request.data['code']
        actual_code = ConfirmationCode.objects.get(profile = user.user_profile)
        if code != actual_code.code:
            return Response({"Error": "Невалидный токен!"}, status = status.HTTP_400_BAD_REQUEST)
        current_datetime = dt.datetime.now(dt.timezone.utc)
        diff = (current_datetime - actual_code.updated_at).total_seconds()
        if diff > 300:
            return Response({"Error": "Токен активации просрочен!"}, status = status.HTTP_400_BAD_REQUEST)
        user.is_verified = True
        user.save()
        return Response({"Success": "User has been verified."}, status = status.HTTP_200_OK)
        
class ResendEmailVerificationCodeAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags = ['Registration'],
        operation_description = "Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "снова отправить код для верификации аккаунта  "
                              "на электронную почту.",
        request_body = resend_swagger['request_body'],                      
        responses = {
            200: "Success.",
            400: "Already verified.",
            404: "Not found.",
        },
    )
    def post(self, request):
        email = request.data['email']
        try:
            user = User.objects.get(email = email)
        except Exception:
            return Response({"Error": "Пользователя с заданным email не существует."}, status = status.HTTP_404_NOT_FOUND)
        if user.is_verified == True:
            return Response({"Error": "Пользователь уже верифицирован."}, status = status.HTTP_400_BAD_REQUEST)
        create_token_and_send_to_email(user = user)
        return Response({"Success": "The verification code has been sent."}, status = status.HTTP_200_OK)

class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['Authorization'],
        operation_description="Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "разлогиниться из приложения "
                              "с помощью токена обновления (Refresh Token). ",
        request_body = logout_swagger['request_body'],
        responses = {
            200: "Success.",
            400: "Invalid token.",
        },
    )
    def post(self, request):
        refresh_token = request.data["refresh"]
        try:
            destroy_token(refresh_token)
            return Response({"Message": "You have successfully logged out."}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"Error": "Ошибка при выходе из учетной записи."}, status=status.HTTP_400_BAD_REQUEST)

class TokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        tags=['Authorization'],
        operation_description="Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "обновить токен доступа (Access Token) "
                              "с помощью токена обновления (Refresh Token). "
                              "Токен обновления позволяет пользователям "
                              "продлить срок действия своего Access Token без "
                              "необходимости повторной аутентификации.",
    )
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)
    
class DeleteUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        tags = ['Authorization'],
        operation_description = "Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "удалить собственный аккаунт. ",
        request_body = delete_swagger['request_body'],
        responses = {
            200: "User is successfully deleted.",
            400: "Invalid token.",
        },
    )
    def delete(self, request, *args, **kwargs):
        refresh_token = request.data['refresh']
        user = request.user
        try:
            destroy_token(refresh_token)
        except Exception:
            return Response({"Error": "Ошибка при удалении пользователя"}, status = status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({'Message': 'User has been successfully deleted.'}, status=status.HTTP_200_OK)