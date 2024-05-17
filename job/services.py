from rest_framework import filters

from authorization.models import Organization


class IsOrganizationFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        organization = Organization.objects.filter(owner=request.user.user_profile).first()
        return queryset.filter(organization=organization)
