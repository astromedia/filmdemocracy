from django.db import models
from django.utils.translation import gettext_lazy as _

from filmdemocracy.registration.models import User
from filmdemocracy.socialclub.models import Club


class FilmDb(models.Model):
    imdb_id = models.CharField('IMDb id', primary_key=True, max_length=7)
    faff_id = models.CharField('FilmAffinity id', default='', max_length=6)
    title = models.CharField(default='', max_length=200)
    year = models.IntegerField(default=0)
    rated = models.CharField(default='', max_length=10)
    duration = models.IntegerField(default=0)
    director = models.CharField(default='', max_length=100)
    writer = models.CharField(default='', max_length=200)
    actors = models.CharField(default='', max_length=300)
    poster_url = models.URLField(default='', max_length=500)
    country = models.CharField(default='', max_length=100)
    language = models.CharField(default='', max_length=20)
    plot = models.CharField(default='', max_length=1000)

    def __str__(self):
        return f'{self.title}/{self.imdb_id}'

    @property
    def imdb_url(self):
        return f'https://www.imdb.com/title/tt{self.imdb_id}/'

    @property
    def faff_url(self):
        return f'https://www.filmaffinity.com/es/film{self.faff_id}.html'


class Film(models.Model):
    """
    Film proposed by user in club. Obtains info from FilmDb.
    """
    id = models.CharField(primary_key=True, max_length=12)  # 5(club)+7(imdb)
    proposed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    filmdb = models.ForeignKey(FilmDb, on_delete=models.CASCADE)
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    seen = models.BooleanField(default=False)
    seen_by = models.ManyToManyField(User, related_name='seen_by')
    seen_date = models.DateField('date seen', null=True, blank=True)

    def __str__(self):
        return f'{self.id}|{self.filmdb.title}'


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    vote_date = models.DateTimeField('date of vote', auto_now_add=True)
    VETO = 'veto'
    SEENNO = 'seenno'
    NO = 'no'
    MEH = 'meh'
    SEENOK = 'seenok'
    YES = 'yes'
    OMG = 'omg'
    vote_choices = (
        (OMG, _('I really really want to see it.')),
        (YES, _('I want to see it.')),
        (SEENOK, _("I've seen it, but I wouldn't mind seeing it again.")),
        (MEH, _('Meh...')),
        (NO, _("I don't want to see it.")),
        (SEENNO, _("I've seen it, and I don't want to see it again.")),
        (VETO, _('Veto!')),
    )
    choice = models.CharField(max_length=6, choices=vote_choices)

    @property
    def vote_karma(self):
        if self.choice in [self.OMG, self.YES, self.SEENOK]:
            return 'positive'
        elif self.choice in [self.MEH]:
            return 'neutral'
        elif self.choice in [self.NO, self.SEENNO, self.VETO]:
            return 'negative'

    def __str__(self):
        return f'{self.user}/{self.film.filmdb.title}/{self.choice}'
