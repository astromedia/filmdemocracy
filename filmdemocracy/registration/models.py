import os

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.db import models


def get_profile_image_path(instance, filename):
    return os.path.join('user_profile_images', str(instance.id), filename)


def get_club_image_path(instance, filename):
    return os.path.join('club_images', str(instance.id), filename)


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


class Club(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=6)
    name = models.CharField('Name of club', max_length=45)
    description = models.TextField(
        _('Club description (optional)'),
        default='',
        max_length=324,
        blank=True,
        null=True
    )
    image = models.ImageField(
        _('club image'),
        upload_to=get_club_image_path,
        blank=True,
        null=True
    )
    admin_user = models.ForeignKey(
        User,
        related_name='admin_user',
        on_delete=models.PROTECT
    )
    users = models.ManyToManyField(
        User,
        related_name='users'
    )

    def __str__(self):
        return f"{self.id}|{self.name}"
