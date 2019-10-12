import os
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


def get_profile_image_path(instance, filename):
    return os.path.join('user_profile_images', str(instance.id), filename)


class User(AbstractUser):
    # TODO: Add country field: https://pypi.org/project/django-countries/
    # TODO: Input image validation

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.CharField(_('public_id'), max_length=36, unique=True)
    email = models.EmailField(_('email'), unique=True,)
    username = models.CharField(_('username'), max_length=20, unique=False,)
    public_email = models.BooleanField(_('Public email in clubs'), default=False)
    first_name = models.CharField(_('first name'), max_length=30, null=True, blank=True,)
    last_name = models.CharField(_('last name'), max_length=150, null=True, blank=True,)
    profile_image = models.ImageField(_('user profile image'), upload_to=get_profile_image_path, blank=True, null=True)
    joined_date = models.DateField('user created date', auto_now_add=True)
    last_updated = models.DateField('user last update date', auto_now=True)
    comment = models.TextField('site admin info about the user', null=True, blank=True, max_length=1000)

    def __str__(self):
        return f"{self.id}|{self.username}|{self.email}"

    def save(self, *args, **kwargs):
        self.public_id = self.public_id or str(self.id)
        return super().save(*args, **kwargs)
