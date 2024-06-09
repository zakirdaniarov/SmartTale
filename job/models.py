from django.db import models
from autoslug import AutoSlugField

from authorization.models import Organization, UserProfile


LOCATION = (
    ('Бишкек', 'Бишкек'),
    ('Каракол', 'Каракол'),
    ('Нарын', 'Нарын'),
    ('Ош', 'Ош'),
    ('Джалал-Абад', 'Джалал-Абад'),
    ('Баткен', 'Баткен'),
    ('Талас', 'Талас')
)

EXPERIENCE = (
    ('Без опыта', 'Без опыта'),
    ('От 1 года до 3 лет', 'От 1 года до 3 лет'),
    ('От 3 лет до 6 лет', 'От 3 лет до 6 лет'),
    ('Более 6 лет', 'Более 6 лет'),
    ('Не имеет значение', 'Не имеет значение')
)

SCHEDULE = (
    ('Полный день', 'Полный день'),
    ('Неполный день', 'Неполный день'),
    ('Частичная занятость', 'Частичная занятость'),
    ('Гибкий график', 'Гибкий график'),
    ('Удаленно', 'Удаленно')
)

CURRENCY = (
    ('Som', 'Som'),
    ('USD', 'USD'),
    ('Ruble', 'Ruble'),
    ('Euro', 'Euro')
)


class Vacancy(models.Model):
    job_title = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from='job_title', unique=True, always_update=True)
    schedule = models.CharField(max_length=60, choices=SCHEDULE, default='Полный день')
    location = models.CharField(max_length=30, choices=LOCATION, default='Бишкек')
    description = models.TextField(max_length=1200, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='org_vacancy')
    user_applicants = models.ManyToManyField(UserProfile, related_name='applied_vacancy', blank=True)
    experience = models.CharField(max_length=30, choices=EXPERIENCE, default='Без опыта')
    min_salary = models.DecimalField(max_digits=10, decimal_places=2)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=15, choices=CURRENCY, default='Som')
    hide = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"This {self.job_title} by {self.organization.title}"


class Resume(models.Model):
    job_title = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from='job_title', unique=True, always_update=True)
    location = models.CharField(max_length=30, choices=LOCATION, null=True, default='Бишкек')
    schedule = models.CharField(max_length=60, choices=SCHEDULE, default='Полный день')
    experience = models.CharField(max_length=30, choices=EXPERIENCE, default='Без опыта')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='author_resume')
    about_me = models.TextField(max_length=1000, null=True)
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=15, choices=CURRENCY, default='Som')
    hide = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"This {self.job_title} by {self.author.first_name}-{self.author.last_name}"


class VacancyResponse(models.Model):
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE)
    applicant = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    cover_letter = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"This response by {self.author.last_name}"
