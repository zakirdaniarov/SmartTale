from django.urls import path

from .views import (EquipmentsListAPIView, EquipmentDetailPageAPIView,
                    CreateEquipmentAPIView, EquipmentSearchAPIView)


urlpatterns = [
    path('equipments/', EquipmentsListAPIView.as_view()),
    path('equipments/search/', EquipmentSearchAPIView.as_view()),
    path('equipments/create/', CreateEquipmentAPIView.as_view()),
    path('equipments/<str:equipment_slug>/', EquipmentDetailPageAPIView.as_view()),
]
