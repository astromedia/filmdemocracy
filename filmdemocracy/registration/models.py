import os
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


def get_profile_image_path(instance, filename):
    return os.path.join('user_profile_images', str(instance.id), filename)


class User(AbstractUser):
    """ Commented values are included in parent class """
    # TODO: Add country field: https://pypi.org/project/django-countries/
    # TODO: Input image validation

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.CharField('public id', max_length=36, unique=True)
    email = models.EmailField('email', unique=True,)
    username = models.CharField('username', max_length=20, unique=False,)
    public_email = models.BooleanField('show email in clubs', default=False)
    profile_image = models.ImageField('user profile image', upload_to=get_profile_image_path, blank=True, null=True)
    # first_name = models.CharField(_('first name'), max_length=30, null=True, blank=True,)
    # last_name = models.CharField(_('last name'), max_length=150, null=True, blank=True,)
    # films_liked = models.ManyToManyField(FilmDb, related_name='films_liked')
    # films_not_liked = models.ManyToManyField(FilmDb, related_name='films_not_liked')
    date_joined = models.DateTimeField('date joined', auto_now_add=True)
    last_updated = models.DateField('user last update date', auto_now=True)
    comment = models.TextField('site admin comments about the user', null=True, blank=True, max_length=1000)

    def __str__(self):
        return f"{self.id}|{self.username}|{self.email}"

    def save(self, *args, **kwargs):
        self.public_id = self.public_id or str(self.id)
        return super().save(*args, **kwargs)
