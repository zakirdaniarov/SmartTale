from django.contrib import admin

from .models import Resume, Vacancy, VacancyResponse

admin.site.register(Resume)
admin.site.register(Vacancy)
admin.site.register(VacancyResponse)