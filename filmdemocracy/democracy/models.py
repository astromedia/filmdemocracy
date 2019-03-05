import os
import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _

from filmdemocracy.registration.models import User
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify


def get_club_logo_path(instance, filename):
    return os.path.join('club_logos', str(instance.id), filename)


class Club(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=5)
    name = models.CharField(_('Club name'), max_length=50)
    short_description = models.CharField(
        _('Short description (Optional)'),
        max_length=120
    )
    panel = MarkdownxField(
        _('Club panel: description, rules, etc. (Optional)'),
        max_length=20000,
        default="## A sample club panel written in markdown"
                "\r\n"
                "\r\n---"
                "\r\n"
                "\r\n#### Point 1: Here is some text. "
                "\r\nHello world, I'm a cinema club... "
                "\r\n"
                "\r\n#### Point 2: And here is a list to consider: "
                "\r\n1. Item #1"
                "\r\n2. Item #2"
                "\r\n3. Item #3"
                "\r\n"
                "\r\n#### Point 3: And here is an unordered list to consider:"
                "\r\n- Item 1"
                "\r\n- Item 2"
                "\r\n- Item 3",
        blank=True,
        null=True,
    )
    # TODO: Input image validation.
    logo = models.ImageField(
        _('club logo'),
        upload_to=get_club_logo_path,
        blank=True,
        null=True,
    )
    members = models.ManyToManyField(User)
    admin_members = models.ManyToManyField(User, related_name='admin_members')

    def __str__(self):
        return f"{self.id}|{self.name}"

    @property
    def formatted_panel(self):
        return markdownify(str(self.panel))


class ShoutboxPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    date = models.DateTimeField('comment date', auto_now_add=True)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)

    def __str__(self):
        return f'{self.user}|{self.text}'


class ClubMemberInfo(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.member}|{self.club}'


class Meeting(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=9)  # 5(club)+4
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    name = models.CharField(_('Name'), default=_('Club meeting'), max_length=50)
    description = models.CharField(_('Description (Optional)'), default='', max_length=5000)
    organizer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    place = models.CharField(_('Place'), default='', max_length=100)
    date = models.DateField(_('Date'))
    time_start = models.TimeField(_('Start time (Optional)'), null=True, blank=True)
    time_end = models.TimeField(_('End time (Optional)'), null=True, blank=True)
    members_yes = models.ManyToManyField(User, related_name='members_yes')
    members_maybe = models.ManyToManyField(User, related_name='members_maybe')

    def __str__(self):
        return f'{self.id}|{self.name}'


class FilmDb(models.Model):
    imdb_id = models.CharField('IMDb id', primary_key=True, max_length=7)
    faff_id = models.CharField('FilmAffinity id', default='', max_length=6)
    title = models.CharField(default='', max_length=1000)
    year = models.IntegerField(default=0)
    rated = models.CharField(default='', max_length=20)
    duration = models.CharField(default='', max_length=20)
    director = models.CharField(default='', max_length=1000)
    writer = models.CharField(default='', max_length=1000)
    actors = models.CharField(default='', max_length=1000)
    poster_url = models.URLField(default='', max_length=1000)
    country = models.CharField(default='', max_length=1000)
    language = models.CharField(default='', max_length=1000)
    plot = models.CharField(default='', max_length=5000)
    last_db_update = models.DateField('last db update date', default=datetime.date.today)

    def __str__(self):
        return f'{self.imdb_id}|{self.title}'

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
    id = models.CharField(primary_key=True, unique=True, max_length=10)  # 5(club)+5
    imdb_id = models.CharField('IMDb id', max_length=7)
    proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
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
        (SEENOK, _("I've seen it, but I wouldn't mind seeing it.")),
        (MEH, _('Meh... I could see it.')),
        (NO, _("I don't want to see it.")),
        (SEENNO, _("I've seen it, and I don't want to see it again.")),
        (VETO, _('Veto!')),
    )
    choice = models.CharField(max_length=6, choices=vote_choices)

    @property
    def vote_karma(self):
        if self.choice in [self.OMG, self.YES, self.SEENOK, self.MEH]:
            return 'positive'
        elif self.choice in [self.NO, self.SEENNO, self.VETO]:
            return 'negative'

    def __str__(self):
        return f'{self.user}|{self.film.filmdb.title}|{self.choice}'


class FilmComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    date = models.DateTimeField('comment date', auto_now_add=True)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)

    def __str__(self):
        return f'{self.user}|{self.film.filmdb.title}|{self.text}'
