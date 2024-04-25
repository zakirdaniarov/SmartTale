import datetime as dt

from django.conf import settings
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.middleware import csrf
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import Response, APIView
from rest_framework_simplejwt import tokens, views as jwt_views
from drf_yasg.utils import swagger_auto_schema

from .serializers import RegistrationSerializer, LoginSerializer, CookieTokenRefreshSerializer
from .models import User, UserProfile, ConfirmationCode
from .services import get_tokens_for_user, create_token_and_send_to_email
from .swagger import login_swagger, resend_swagger, verify_swagger, register_swagger

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
        serializer.save()
        user = User.objects.get(email = serializer.validated_data['email'])
        try:
            UserProfile.objects.create(user = user, first_name = first_name, last_name = last_name, middle_name = middle_name)
        except Exception as e:
            user.delete()
            return Response({'Invalid data': 'Invalid first, last or middle names.'}, status = status.HTTP_400_BAD_REQUEST)
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
            403: "Not verified.",
            404: "Not found.",
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        response = Response()
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(email = email, password=password)

        if user is not None:
            if user.is_verified:
                data = get_tokens_for_user(user)
                response.set_cookie(
                    key = settings.SIMPLE_JWT['AUTH_COOKIE'],
                    value = data['access_token'],
                    expires = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                    secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                    httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                    samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
                )
                response.set_cookie(
                    key = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
                    value = data['refresh_token'],
                    expires = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                    secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                    httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                    samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
                )
                data['X-CSRFToken'] = csrf.get_token(request)
                response.data = data
                response.status_code = 200
                return response
            else:
                return Response({"Not verified" : "This account is not verified!"}, status = status.HTTP_403_FORBIDDEN)
        else:
            return Response({"Invalid" : "Invalid username or password!!"}, status = status.HTTP_404_NOT_FOUND)

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
            return Response({"Already verified": "User is already verified."}, status = status.HTTP_400_BAD_REQUEST)
        code = request.data['code']
        actual_code = ConfirmationCode.objects.get(profile = user.user_profile)
        if code != actual_code.code:
            return Response({"Invalid": "Invalid token."}, status = status.HTTP_400_BAD_REQUEST)
        current_datetime = dt.datetime.now(dt.timezone.utc)
        print(current_datetime)
        print(actual_code.updated_at)
        diff = (current_datetime - actual_code.updated_at).total_seconds()
        if diff > 300:
            return Response({"Expired": "Activation token has expired."}, status = status.HTTP_400_BAD_REQUEST)
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
            404: "Not found.",
        },
    )
    def post(self, request):
        email = request.data['email']
        user = get_object_or_404(User, email = email)
        create_token_and_send_to_email(user = user)
        return Response({"Success": "The verification code has been sent."}, status = status.HTTP_200_OK)

class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags = ['Authorization'],
        operation_description = "Этот эндпоинт предоставляет "
                              "возможность пользователю "
                              "выйти из аккаунта. ",                   
        responses = {
            200: "Success.",
            400: "Invalid.",
        },
    )
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
            token = tokens.RefreshToken(refresh_token)
            token.blacklist()

            response = Response()
            response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE'])
            response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
            response.delete_cookie("X-CSRFToken")
            response.delete_cookie("csrftoken")
            response["X-CSRFToken"] = None
            response.status_code = 200
            return response
        except:
            return Response({"Invalid": "Token is invalid."}, status = status.HTTP_400_BAD_REQUEST)
        
class CookieTokenRefreshView(jwt_views.TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        response.set_cookie(
            key = settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
            value = response.data['refresh'],
            expires = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
            secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
        )
        response.set_cookie(
            key = settings.SIMPLE_JWT['AUTH_COOKIE'],
            value = response.data['access'],
            expires = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
            secure = settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly = settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
            samesite = settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
        )
        del response.data["refresh"]
        response["X-CSRFToken"] = request.COOKIES.get("csrftoken")
        return super().finalize_response(request, response, *args, **kwargs)