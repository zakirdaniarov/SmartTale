from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from authorization.models import Organization
from monitoring.models import Employee, STATUS_CHOICES


class CurrentUserOrReadOnly(IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if type(obj) == type(user) and obj == user:
            return True
        return request.method in SAFE_METHODS


class AddVacancyEmployee(IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user.user_profile
        current_organization = Organization.objects.filter(owner=user).first()
        if not current_organization:
            return False
        if user == current_organization.founder or user == current_organization.owner:
            return True

        employee = Employee.objects.filter(user=user, org=current_organization).first()
        if employee and employee.job_title and employee.job_title.flag_create_vacancy:
            return True
        return False


class IsOrganizationEmployeeReadOnly(IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user

        if user and not user.is_anonymous:
            employee = Employee.objects.filter(user = user.user_profile, status = STATUS_CHOICES[0][0], active = True).first()
            if not employee:
                return False
        else:
            return False
