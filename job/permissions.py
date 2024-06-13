from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from authorization.models import Organization
from monitoring.models import Employee


class CurrentUserOrReadOnly(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if type(obj) == type(user) and obj == user:
            return True
        return request.method in SAFE_METHODS


class AddVacancyEmployee(IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user.user_profile
        current_organization = Organization.objects.filter(owner=request.user.user_profile).first()
        if not current_organization:
            return False
        if user == current_organization.founder or current_organization.owner:
            return True

        employee = Employee.objects.filter(user=user, org=current_organization).first()
        if employee and employee.job_title:
            if employee.job_title.flag_create_jobtitle and employee.job_title.flag_remove_jobtitle:
                return True
        return False


class IsOrganizationEmployeeReadOnly(IsAuthenticated):
    def has_permission(self, request, view):
        anonymous_user = request.user

        if anonymous_user and not anonymous_user.is_anonymous:

            if request.method in SAFE_METHODS:
                current_organization = Organization.objects.filter(owner=request.user.user_profile).first()
                employee = request.user.user_profile
                if employee == current_organization.founder or employee == current_organization.owner:
                    return True

                if current_organization:
                    return Employee.objects.filter(user=request.user.user_profile, org=current_organization).exists()
            return False
        else:
            return False
