import os

from django.utils.translation import gettext_lazy as _
from django.db import models

from filmdemocracy.registration.models import User
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify


def get_club_logo_path(instance, filename):
    return os.path.join('club_logos', str(instance.id), filename)


class Club(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=5)
    name = models.CharField('Club name', max_length=40)
    short_description = models.TextField(
        _('Short club description'),
        max_length=100,
    )
    club_description = MarkdownxField(
        _('Club description / rules (optional)'),
        max_length=1000,
        default='',
        blank=True,
        null=True
    )
    # TODO: Input image validation.
    logo = models.ImageField(
        _('club logo'),
        upload_to=get_club_logo_path,
        blank=True,
        null=True,
    )
    admin_users = models.ManyToManyField(
        User,
        related_name='admin_users',
    )
    users = models.ManyToManyField(User)

    def __str__(self):
        return f"{self.id}|{self.name}"

    @property
    def formatted_long_description(self):
        return markdownify(str(self.club_description))
