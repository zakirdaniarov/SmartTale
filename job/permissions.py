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
            # Проверяем, является ли метод запроса безопасным (например, GET, HEAD, OPTIONS)
            if request.method in SAFE_METHODS:
                # Получаем организацию, где пользователь является владельцем
                current_organization = Organization.objects.filter(founder=user.user_profile).first()
                if current_organization:
                    employee = user.user_profile
                    # Проверяем, является ли пользователь основателем или владельцем организации
                    if employee == current_organization.founder or employee == current_organization.owner:
                        return True
                    # Проверяем, является ли пользователь сотрудником организации
                    if Employee.objects.filter(user=user.user_profile, org=current_organization).exists():
                        return True
            # Если метод запроса не безопасный, запрещаем доступ
            return False
        else:
            # Если пользователь анонимный, запрещаем доступ
            return False
