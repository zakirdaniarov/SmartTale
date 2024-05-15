from rest_framework import views, status, permissions
from rest_framework.response import Response

from .models import Vacancy, Resume
from .serializers import VacancySerializer, ResumeSerializer
from .permissions import CurrentUserOrReadOnly


class VacancyListAPIView(views.APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.all().order_by('-created_at')
        except Vacancy.DoesNotExist:
            return Response({"error": "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)
        serializer = VacancySerializer(vacancy, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddVacancyAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = VacancySerializer(data=request.data)
        if serializer.is_valid():
            current_organization = request.user.user_profile.current_member
            organization = serializer.validated_data['organization'] = current_organization
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeVacancyAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def put(self, request, *args, **kwargs):
        ...


class DeleteVacancyAPIView(views.APIView):
    permission_classes = [CurrentUserOrReadOnly]

    def post(self, request, *args, **kwargs):
        try:
            vacancy = Vacancy.objects.get(slug=kwargs['vacancy_slug'])
        except Vacancy.DoesNotExist:
            return Response({'error': "Vacancy does not exist"}, status=status.HTTP_404_NOT_FOUND)

        organization = request.user

        if organization == 'org_vacancy':
            vacancy.delete()
        else:
            return Response({"error": "Only organization that added it can delete"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Successfully deleted"}, status=status.HTTP_200_OK)

