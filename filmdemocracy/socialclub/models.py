import os

from django.utils.translation import gettext_lazy as _
from django.db import models

from filmdemocracy.registration.models import User


def get_club_logo_path(instance, filename):
    return os.path.join('club_logos', str(instance.id), filename)


class Club(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=5)
    name = models.CharField('Club name', max_length=40)
    short_description = models.TextField(
        _('Short club description'),
        max_length=100,
    )
    long_description = models.TextField(
        _('Long club description / rules (optional)'),
        default='',
        max_length=1000,
        blank=True,
        null=True
    )
    logo = models.ImageField(
        _('club logo'),
        upload_to=get_club_logo_path,
        blank=True,
        null=True
    )
    admin_users = models.ManyToManyField(
        User,
        related_name='admin_users',
    )
    users = models.ManyToManyField(User)

    def __str__(self):
        return f"{self.id}|{self.name}"
