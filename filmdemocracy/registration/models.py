import os

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


def get_profile_image_path(instance, filename):
    return os.path.join('user_profile_images', str(instance.id), filename)


class User(AbstractUser):
    # TODO: Add country field: https://pypi.org/project/django-countries/
    email = models.EmailField(
        _('email'),
        unique=True,
    )
    first_name = models.CharField(
        _('first name'),
        max_length=30,
        null=True,
        blank=True,
    )
    last_name = models.CharField(
        _('last name'),
        max_length=150,
        null=True,
        blank=True,
    )
    profile_image = models.ImageField(
        _('user profile image'),
        upload_to=get_profile_image_path,
        blank=True,
        null=True
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.id}|{self.username}|{self.email}"
