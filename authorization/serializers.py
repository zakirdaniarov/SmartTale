from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User

class RegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length = 50)
    last_name = serializers.CharField(max_length = 50)
    middle_name = serializers.CharField(max_length = 50)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=15, min_length=8, write_only=True)
    password_confirm = serializers.CharField(max_length=15, min_length=8, write_only=True)

    def validate(self, data):
        user = User.objects.filter(email = data['email']).first()
        if user is not None:
            raise ValidationError("User with this email already exists.")
        if data['password'] != data['password_confirm']:
            raise ValidationError("Passwords don't match")
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)
    
class CheckEmailSeriailizer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['email']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        style={"input_type": "password"}, write_only=True)
