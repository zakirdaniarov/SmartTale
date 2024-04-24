from rest_framework.filters import SearchFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Equipment
from .serializers import EquipmentSerializer, EquipmentDetailSerializer


class EquipmentsListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            equipments = Equipment.objects.all()
        except Equipment.DoesNotExist:
            return Response({"error": "Equipments does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentSerializer(equipments, many=True)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)


class CreateEquipmentAPIView(APIView):
    def post(self, request, *args, **kwargs):
        equipment_serializer = EquipmentDetailSerializer(data=request.data)
        if equipment_serializer.is_valid():
            equipment_serializer.save()
            return Response(equipment_serializer.data, status=status.HTTP_201_CREATED)
        return Response(equipment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EquipmentSearchAPIView(APIView):
    filter_backends = [SearchFilter]
    search_fields = ['title']

    def get(self, request, *args, **kwargs):
        try:
            search_query = request.query_params.get('search', '')
            equipment = Equipment.objects.filter(title__icontains=search_query)
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentSerializer(equipment, many=True)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)


class EquipmentDetailPageAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(equipment)
        return Response(equipment_serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Equipment does not exist"}, status=status.HTTP_404_NOT_FOUND)
        equipment_serializer = EquipmentDetailSerializer(instance=equipment, data=request.data)
        if equipment_serializer.is_valid():
            equipment_serializer.save()
            return Response(equipment_serializer.data, status=status.HTTP_200_OK)
        return Response(equipment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        try:
            equipment = Equipment.objects.get(slug=kwargs['equipment_slug'])
        except Equipment.DoesNotExist:
            return Response({"error": "Error when deleting"}, status=status.HTTP_400_BAD_REQUEST)
        equipment.delete()
        return Response({"data": "Successfully deleted"}, status=status.HTTP_200_OK)
