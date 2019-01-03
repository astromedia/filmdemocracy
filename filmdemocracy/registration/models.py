import os

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.db import models


def get_profile_image_path(instance, filename):
    return os.path.join('user_profile_images', str(instance.id), filename)


class User(AbstractUser):
    email = models.EmailField(
        _('email'),
        unique=True,
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
