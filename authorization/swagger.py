from rest_framework import serializers

class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    class Meta:
        abstract = True

class RegistrationRequestSerializer(LoginRequestSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    middle_name = serializers.CharField()
    password_confirm = serializers.CharField()


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    class Meta:
        abstract = True

class ResendRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    class Meta:
        abstract = True

class VerifyRequestSerializer(ResendRequestSerializer):
    code = serializers.CharField()

class LoginDataSerializer(serializers.Serializer):
    subscription = serializers.DateTimeField()
    is_subscribed = serializers.BooleanField()
class TokenResponseSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
    access_token = serializers.CharField()
    data = LoginDataSerializer()

    class Meta:
        abstract = True

register_swagger = {
    'parameters': None,
    'request_body': RegistrationRequestSerializer,
    'response': None,
}

login_swagger = {
    'parameters': None,
    'request_body': LoginRequestSerializer,
    'response': TokenResponseSerializer
}

verify_swagger = {
    'parameters': None,
    'request_body': VerifyRequestSerializer,
    'response': None,
}

resend_swagger = {
    'parameters': None,
    'request_body': ResendRequestSerializer,
    'response': None
}

logout_swagger = {
    'parameters': None,
    'request_body': RefreshTokenSerializer,
    'response': None
}

delete_swagger = {
    'parameters': None,
    'request_body': RefreshTokenSerializer,
    'response': None
}