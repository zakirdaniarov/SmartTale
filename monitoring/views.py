import datetime as dt

from rest_framework.views import status, Response, APIView
from rest_framework.permissions import IsAuthenticated
from authorization.models import Organization

from .serializers import (JobTitleSeriailizer, OrganizationSerializer, ProfileDetailSerializer,
                          EmployeeListSerializer)
from .models import Employee, JobTitle
from authorization.models import UserProfile

class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug, *args, **kwargs):
        try:
            user = UserProfile.objects.get(slug = slug)
        except Exception:
            return Response({"Not found.": "User is not found."}, status = status.HTTP_404_NOT_FOUND)
        serializer = ProfileDetailSerializer(user)
        return Response(serializer.data, status = status.HTTP_200_OK)

class OrganizationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.user_profile.sub_type == 'No sub':
            return Response({"No permission": "You don't have permission for creating organization!"}, status = status.HTTP_403_FORBIDDEN)
        if user.user_profile.sub_type == 'Premium':
            if Organization.objects.filter(owner = user.user_profile).count() == 5:
                return Response({"Invalid.": "You've reached max number of organizations you can create (5)!"}, status = status.HTTP_400_BAD_REQUEST)
        else:
            if user.user_profile.subscription < dt.datetime.now(dt.timezone.utc):
                return Response({"Invalid.": "Your subscription has expired!"}, status = status.HTTP_400_BAD_REQUEST)
        serializer = OrganizationSerializer(data = request.data, context = {'user': user.user_profile})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.
class CreateJobTitleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        try:
            employee = Employee.objects.get(user = user.user_profile)
            if not employee.job_title and not employee.job_title.flag_create_jobtitle:
                raise Exception("No permission")
        except Exception:
            return Response({"No permission": "You don't have permission for creating job title!"}, status = status.HTTP_403_FORBIDDEN)
        serializer = JobTitleSeriailizer(data = request.data, context = {'org': employee.org})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeleteJobTitleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        try:
            employee = Employee.objects.get(user = user.user_profile)
            if not employee.job_title and not employee.job_title.flag_delete_jobtitle:
                raise Exception("No permission")
        except Exception:
            return Response({"No permission": "You don't have permission for creating job title!"}, status = status.HTTP_403_FORBIDDEN)
        job_title = JobTitle.objects.get(org = employee.org, title = request.data['title'])
        job_title.delete()
        return Response({"Success": "Job title has been deleted!"}, status = status.HTTP_200_OK)
    
class EmployeeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        employees = Employee.objects.filter(org = user.user_profile.working_org)
        serializer = EmployeeListSerializer(employees, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
