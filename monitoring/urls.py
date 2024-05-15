from django.urls import path, include

from .views import (UserDetailAPIView, OrganizationAPIView, EmployeeListAPIView,
                    CreateJobTitleAPIView, DeleteJobTitleAPIView, JobTitleListAPIView,
                    EmployeeDetailAPIView, OrganizationDetailAPIView, OrganizationListAPIView)


urlpatterns = [
    path('u/<slug:userprofile_slug>', UserDetailAPIView.as_view(), name = 'user-detail-profile'),
    path('organization/create', OrganizationAPIView.as_view(), name = 'organization-create'),
    path('organization/<slug:org_slug>', OrganizationDetailAPIView.as_view(), name='organization-detail'),
    path('organization/list', OrganizationListAPIView.as_view(), name = 'organization-list'),
    path('employees/list', EmployeeListAPIView.as_view(), name = 'employees-list'),
    path('employees/<slug:employee_slug>', EmployeeDetailAPIView.as_view(), name = 'employees-detail'),
    path('org-jobs/delete', DeleteJobTitleAPIView.as_view(), name = 'jobtitles-delete'),
    path('org-jobs/add', CreateJobTitleAPIView.as_view(), name = 'jobtitles-add'),
    path('org-jobs/list', JobTitleListAPIView.as_view(), name = 'jobtitles-list'),
]