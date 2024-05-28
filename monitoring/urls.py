from django.urls import path, include

from .views import (UserDetailAPIView, OrganizationAPIView, EmployeeListAPIView,
                    CreateJobTitleAPIView, DeleteJobTitleAPIView, JobTitleListAPIView,
                    EmployeeDetailAPIView, OrganizationDetailAPIView, OrganizationListAPIView,
                    EmployeeCreateAPIView, EmployeeDeleteAPIView, SubscriptionAPIView,
                    MyProfileAPIView, UserAdsAPIView, EmployeeOrdersAPIView)


urlpatterns = [
    path('u/<slug:userprofile_slug>', UserDetailAPIView.as_view(), name = 'user-detail-profile'),
    path('u-ads/<slug:userprofile_slug>', UserAdsAPIView.as_view(), name = 'user-detail-profile'),
    path('myprofile', MyProfileAPIView.as_view(), name = 'my-profile'),
    path('organization/create', OrganizationAPIView.as_view(), name = 'organization-create'),
    path('organization/<slug:org_slug>', OrganizationDetailAPIView.as_view(), name='organization-detail'),
    path('organization/list', OrganizationListAPIView.as_view(), name = 'organization-list'),
    path('employees/list', EmployeeListAPIView.as_view(), name = 'employees-list'),
    path('employees/<slug:employee_slug>', EmployeeDetailAPIView.as_view(), name = 'employees-detail'),
    path('employees-order/<slug:employee_slug>', EmployeeOrdersAPIView.as_view(), name = 'employees-detail'),
    path('org-jobs/delete', DeleteJobTitleAPIView.as_view(), name = 'jobtitles-delete'),
    path('org-jobs/add', CreateJobTitleAPIView.as_view(), name = 'jobtitles-add'),
    path('org-jobs/list', JobTitleListAPIView.as_view(), name = 'jobtitles-list'),
    path('employee/delete', EmployeeDeleteAPIView.as_view(), name = 'employee-delete'),
    path('employee/add', EmployeeCreateAPIView.as_view(), name = 'employee-add'),
    path('subscribe', SubscriptionAPIView.as_view(), name = 'subscribe'),
]
