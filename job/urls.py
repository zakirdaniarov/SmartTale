from django.urls import path

from .views import (VacancyListAPIView, AddVacancyAPIView, ChangeVacancyAPIView, DeleteVacancyAPIView,
                    ResumeListAPIView, AddResumeAPIView, ChangeResumeAPIView, DeleteResumeAPIView,
                    VacancySearchAPIView, SearchResumeAPIView, VacancyDetailAPIView, ResumeDetailAPIView,
                    VacancyByOrgAPIView, ResumeByAuthorAPIView, ResumeHideAPIView, VacancyHideAPIView,
                    AddVacancyResponseAPIVIew, VacancyResponseListAPIView)


urlpatterns = [
    path('vacancy/', VacancyListAPIView.as_view()),
    path('vacancy/<slug:vacancy_slug>/', VacancyDetailAPIView.as_view()),
    path('add-vacancy/', AddVacancyAPIView.as_view()),
    path('change-vacancy/<slug:vacancy_slug>/', ChangeVacancyAPIView.as_view()),
    path('delete-vacancy/<slug:vacancy_slug>/', DeleteVacancyAPIView.as_view()),
    path('vacancy/search/', VacancySearchAPIView.as_view()),
    path('org-vacancy/', VacancyByOrgAPIView.as_view()),
    path('vacancy/hide/<vacancy_slug>/', VacancyHideAPIView.as_view()),
    path('vacancy-response-list/', VacancyResponseListAPIView.as_view()),
    path('vacancy-response/<slug:vacancy_slug>/', AddVacancyResponseAPIVIew.as_view()),

    path('resume/', ResumeListAPIView.as_view()),
    path('resume/<slug:resume_slug>/', ResumeDetailAPIView.as_view()),
    path('add-resume/', AddResumeAPIView.as_view()),
    path('change-resume/<slug:resume_slug>/', ChangeResumeAPIView.as_view()),
    path('delete-resume/<slug:resume_slug>/', DeleteResumeAPIView.as_view()),
    path('resume/search/', SearchResumeAPIView.as_view()),
    path('my-resume/', ResumeByAuthorAPIView.as_view()),
    path('resume/hide/<resume_slug>/', ResumeHideAPIView.as_view())
]
