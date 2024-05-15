from django.urls import path

from .views import VacancyListAPIView, AddVacancyAPIView


urlpatterns = [
    path('vacancy/', VacancyListAPIView.as_view()),
    path('add-vacancy/', AddVacancyAPIView.as_view())
]
