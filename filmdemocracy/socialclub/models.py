import os

from django.utils.translation import gettext_lazy as _
from django.db import models

from filmdemocracy.registration.models import User


def get_club_image_path(instance, filename):
    return os.path.join('club_images', str(instance.id), filename)


class Club(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=5)
    name = models.CharField('Club name', max_length=40)
    short_description = models.TextField(
        _('Short club description'),
        max_length=100,
    )
    club_rules = models.TextField(
        _('Club rules (optional)'),
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
    users = models.ManyToManyField(User)

    def __str__(self):
        return f"{self.id}|{self.name}"
