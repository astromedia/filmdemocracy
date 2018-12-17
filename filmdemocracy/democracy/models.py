from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Film(models.Model):
    title = models.CharField(default='', max_length=200)
    imdb_id = models.CharField('IMDb id', default='', max_length=10)
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    proposed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    seen = models.BooleanField(default=False)
    seen_date = models.DateField('date seen', null=True, blank=True)

    def __str__(self):
        return f'{self.title}/{self.imdb_id}'

    @property
    def imdb_url(self):
        return f'https://www.imdb.com/title/{self.imdb_id}/'


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    vote_date = models.DateTimeField('date of vote', auto_now_add=True)
    VETO = 'veto'
    SEENNO = 'seenno'
    NO = 'no'
    MEH = 'meh'
    SEENOK = 'seenok'
    YES = 'yes'
    OMG = 'omg'
    vote_choices = (
        (VETO, _('Veto!')),
        (SEENNO, _("I've seen it and I don't want to see it again.")),
        (NO, _("I don't want to see it.")),
        (MEH, _('Meh...')),
        (SEENOK, _("I've seen it and I wouldn't mind seeing it again.")),
        (YES, _('I want to see it.')),
        (OMG, _('I really want to see it.')),
    )
    choice = models.CharField(max_length=7, choices=vote_choices, default=MEH)

    def __str__(self):
        return f'{self.user}/{self.film}/{self.choice}'
