from django.conf import settings
from django.contrib.auth import authenticate
from django.middleware import csrf
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import Response, APIView
from rest_framework_simplejwt import tokens, views as jwt_views

from .serializers import RegistrationSerializer, LoginSerializer, CookieTokenRefreshSerializer
from .models import User, UserProfile
from .services import get_tokens_for_user, create_token_and_send_to_email

class SignupAPIView(APIView):
    permission_classes = [AllowAny]

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
                response.data = {"Success" : "Login successfully", "data": data}
                response.status_code = 200
                return response
            else:
                return Response({"Not verified" : "This account is not verified!"}, status = status.HTTP_403_FORBIDDEN)
        else:
            return Response({"Invalid" : "Invalid username or password!!"}, status = status.HTTP_404_NOT_FOUND)
        
class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get(settings.SIMPLE_JWT(['AUTH_COOKIE_REFRESH']))
            token = tokens.RefreshToken(refresh_token)
            token.blacklist()

            response = Response()
            response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE'])
            response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
            response.delete_cookie('X-CRSFToken')
            response.status_code = 200
            return response
        except:
            return Response({"Invalid": "Token is invalid."}, status = status.HTTP_400_BAD_REQUEST)
        
class CookieTokenRefreshView(jwt_views.TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get("refresh"):
            response.set_cookie(
                key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
                value=response.data['refresh'],
                expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
            )

            del response.data["refresh"]
        response["X-CSRFToken"] = request.COOKIES.get("csrftoken")
        return super().finalize_response(request, response, *args, **kwargs)