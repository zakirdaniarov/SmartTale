from django.urls import path, include

from .views import *


urlpatterns = [
    path('u/<slug:userprofile_slug>/', UserDetailAPIView.as_view(), name = 'user-detail-profile'),
    path('u-ads/<slug:userprofile_slug>', UserAdsAPIView.as_view(), name = 'user-order-profile'),
    path('my-profile/', MyProfileAPIView.as_view(), name = 'my-profile'),
    path('organization/create/', OrganizationAPIView.as_view(), name = 'organization-create'),
    path('organization/activate/<slug:org_slug>/', OrganizationActivateAPIView.as_view(), name = 'organization-activate'),
    path('organization/detail/<slug:org_slug>/', OrganizationDetailAPIView.as_view(), name='organization-detail'),
    path('my-orgs/', OrganizationListAPIView.as_view(), name = 'organization-list'),
    path('employee/list/', EmployeeListAPIView.as_view(), name = 'employee-list'),
    path('employee/add/', EmployeeCreateAPIView.as_view(), name = 'employee-add'),
    path('employee/detail/<slug:employee_slug>/', EmployeeDetailAPIView.as_view(), name = 'employee-detail'),
    path('employee-order/<slug:employee_slug>/', EmployeeOrdersAPIView.as_view(), name = 'employee-order-detail'),
    path('employee/exit/', EmployeeExitAPIView.as_view(), name = 'employee-exit'),
    path('employee/apply/', EmployeeApplyAPIView.as_view(), name = 'employee-apply'),
    path('employee/decline/', EmployeeDeclineAPIView.as_view(), name = 'employee-decline'),
    path('employee/invites/', OrgInvitesAPIView.as_view(), name = 'employee-invites'),
    path('order-employees/<slug:order_slug>/', OrderEmployeesAPIView.as_view(), name='order-employees'),
    path('org-jobs/add/', CreateJobTitleAPIView.as_view(), name = 'jobtitles-add'),
    path('org-jobs/detail/<slug:jt_slug>/', JobTitleAPIView.as_view(), name = 'jobtitles-detail'),
    path('org-jobs/list/', JobTitleListAPIView.as_view(), name = 'jobtitles-list'),
    path('subscribe/', SubscriptionAPIView.as_view(), name = 'subscribe'),
]
