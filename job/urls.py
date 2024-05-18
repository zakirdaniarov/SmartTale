from django.urls import path

from .views import (VacancyListAPIView, AddVacancyAPIView, ChangeVacancyAPIView, DeleteVacancyAPIView,
                    ResumeListAPIView, AddResumeAPIView, ChangeResumeAPIView, DeleteResumeAPIView,
                    VacancySearchAPIView, SearchResumeAPIView, VacancyFilterAPIView, ResumeFilterAPIView)


urlpatterns = [
    path('vacancy/', VacancyListAPIView.as_view()),
    path('add-vacancy/', AddVacancyAPIView.as_view()),
    path('change-vacancy/<slug:vacancy_slug>/', ChangeVacancyAPIView.as_view()),
    path('delete-vacancy/<slug:vacancy_slug>/', DeleteVacancyAPIView.as_view()),
    path('vacancy/search/', VacancySearchAPIView.as_view()),
    path('vacancy/filter/', VacancyFilterAPIView.as_view()),

    path('resume/', ResumeListAPIView.as_view()),
    path('add-resume/', AddResumeAPIView.as_view()),
    path('change-resume/<slug:resume_slug>/', ChangeResumeAPIView.as_view()),
    path('delete-resume/<slug:resume_slug>/', DeleteResumeAPIView.as_view()),
    path('resume/search/', SearchResumeAPIView.as_view()),
    path('resume/filter/', ResumeFilterAPIView.as_view()),
]
