import os
import datetime
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.urls import reverse_lazy

from markdownx.models import MarkdownxField
from markdownx.utils import markdownify

from filmdemocracy.registration.models import User


CLUB_ID_N_DIGITS = 6
FILM_ID_N_DIGITS = 6
INVITATION_DURATION_DAYS = 30


def get_club_logo_image_path(instance, filename):
    return os.path.join('club_logos', str(instance.id), filename)


class Club(models.Model):
    # TODO: Input image validation

    DEFAULT_PANEL_STRING = _("""#### A sample club panel
    \rSome normal text, *italic text*, **strong text** and **_strong italic text_** here...
    \r##### Here is a list:\r1. Item #1\r2. Item #2""")

    id = models.CharField(primary_key=True, unique=True, max_length=CLUB_ID_N_DIGITS)
    name = models.CharField('club name', max_length=50)
    short_description = models.CharField('short description', max_length=120)
    panel = MarkdownxField(
        'club panel: description, rules, etc. (optional)',
        max_length=20000,
        default=DEFAULT_PANEL_STRING,
        blank=True,
        null=True,
    )
    logo_image = models.ImageField('club logo image', upload_to=get_club_logo_image_path, blank=True, null=True)
    founder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='founder')
    members = models.ManyToManyField(User)
    admin_members = models.ManyToManyField(User, related_name='admin_members')
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)
    comment = models.TextField('site admin comments about the club', null=True, blank=True, max_length=1000)

    def __str__(self):
        return f"{self.id}|{self.name}"

    @property
    def formatted_panel(self):
        return markdownify(str(self.panel))


class Invitation(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    inviter = models.ForeignKey(User, on_delete=models.CASCADE)
    hash_invited_email = models.CharField(max_length=64)
    invitation_text = models.CharField('invitation message (optional)', max_length=500)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)

    def __str__(self):
        return f"{str(self.id)}|{self.club.name}|{self.inviter.username}"


class ClubMemberInfo(models.Model):

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    date_joined_club = models.DateField(auto_now_add=True)
    admin_comment = models.TextField('club admins comments about the member', null=True, blank=True, max_length=2000)

    def __str__(self):
        return f'{self.member}|{self.club}'


class Meeting(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    name = models.CharField('name', max_length=50)
    description = models.CharField('description (optional)', default='', max_length=5000)
    organizer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    place = models.CharField('place', max_length=100)
    date = models.DateField('date')
    time_start = models.TimeField('time start (optional)', null=True, blank=True)
    active = models.BooleanField(default=True)
    members_yes = models.ManyToManyField(User, related_name='members_yes')
    members_maybe = models.ManyToManyField(User, related_name='members_maybe')
    members_no = models.ManyToManyField(User, related_name='members_no')
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)

    def __str__(self):
        return f'{self.id}|{self.name}'


class FilmDb(models.Model):

    imdb_id = models.CharField('IMDb id', primary_key=True, max_length=8)
    faff_id = models.CharField('FilmAffinity id', default='', max_length=6)
    imdb_rating = models.CharField('IMDb rating', default='', max_length=4)
    imdb_votes = models.IntegerField('IMDb votes', default=0)
    metascore = models.CharField('Metascore', default='', max_length=3)
    title = models.CharField(default='', max_length=1000)
    original_title = models.CharField(default='', max_length=1000)
    adult_film = models.BooleanField(default=False)
    year = models.IntegerField(default=0)
    rated = models.CharField(default='', max_length=20)
    duration = models.CharField(default='', max_length=20)
    director = models.CharField(default='', max_length=2000)
    writer = models.CharField(default='', max_length=2000)
    actors = models.CharField(default='', max_length=2000)
    poster_url = models.URLField(default='', max_length=1000)
    country = models.CharField(default='', max_length=1000)
    language = models.CharField(default='', max_length=1000)
    plot = models.CharField(default='', max_length=20000)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)
    comment = models.TextField('site admin comments about the film', null=True, blank=True, max_length=1000)

    def __str__(self):
        return f'{self.title}'

    @property
    def slug(self):
        return slugify(self.title)

    @property
    def duration_in_mins_int(self):
        """ Util to safely obtain the film duration in minutes (int) """
        duration = str(self.duration)
        try:
            duration_int = int(duration)
        except ValueError:
            if ' min' in self.duration:
                duration_int = int(duration.replace(' min', ''))
            elif 'min' in self.duration:
                duration_int = int(duration.replace('min', ''))
            else:
                duration_int = 0
        return duration_int

    @property
    def duration_str(self):
        """ Display this string as the film duration """
        duration_str = str(self.duration)
        try:
            duration_int = int(duration_str)
            return '{} min'.format(duration_int)
        except ValueError:
            if ' min' in duration_str:
                return duration_str
            elif 'min' in duration_str:
                return duration_str.replace('min', ' min')
            else:
                return duration_str

    @property
    def imdb_url(self):
        return f'https://www.imdb.com/title/tt{self.imdb_id}/'

    @property
    def metascore_url(self):
        return f'https://www.imdb.com/title/tt{self.imdb_id}/criticreviews'

    @property
    def clean_imdb_rating(self):
        return self.imdb_rating if self.imdb_rating != 'N/A' else None

    @property
    def clean_metascore(self):
        return self.metascore if self.metascore != 'N/A' else None

    @property
    def faff_url(self):
        return f'https://www.filmaffinity.com/es/film{self.faff_id}.html'

    @property
    def updatable(self):
        time_diff_created = datetime.datetime.now().date() - self.created_datetime.date()
        time_diff_updated = self.last_updated_datetime - self.created_datetime
        return time_diff_created > 2 * time_diff_updated


class FilmDbTranslation(models.Model):

    imdb_id = models.CharField('IMDb id', default='', max_length=8)
    title = models.CharField(default='', max_length=1000)
    language_code = models.CharField(default='', max_length=3)


class Film(models.Model):
    """ Film proposed by user in club. Obtains info from FilmDb. """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.CharField(unique=False, max_length=FILM_ID_N_DIGITS)
    proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    db = models.ForeignKey(FilmDb, on_delete=models.CASCADE)
    seen = models.BooleanField(default=False)
    marked_seen_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_seen_by')
    seen_by = models.ManyToManyField(User, related_name='seen_by')
    seen_date = models.DateField('date seen', null=True, blank=True)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)

    def __str__(self):
        return f'{self.id}|{self.db.title}'

    @property
    def share_link(self):
        return reverse_lazy('democracy:film_detail', kwargs={'club_id': self.club.id,
                                                             'film_public_id': self.public_id,
                                                             'film_slug': self.db.slug})


class Vote(models.Model):

    OMG = 'omg'
    YES = 'yes'
    SEENOK = 'seenok'
    MEH = 'meh'
    NO = 'no'
    SEENNO = 'seenno'
    VETO = 'veto'

    vote_choices = (
        (OMG, _('I really really want to see it.')),
        (YES, _('I want to see it.')),
        (SEENOK, _("I've seen it, but I wouldn't mind seeing it.")),
        (MEH, _('Meh... I could see it.')),
        (NO, _("I don't want to see it.")),
        (SEENNO, _("I've seen it, and I don't want to see it again.")),
        (VETO, _('Veto!')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    choice = models.CharField(max_length=6, choices=vote_choices)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)

    @property
    def vote_karma(self):
        if self.choice in [self.OMG, self.YES, self.SEENOK]:
            return 'positive'
        elif self.choice == self.MEH:
            return 'neutral'
        elif self.choice in [self.NO, self.SEENNO, self.VETO]:
            return 'negative'

    @property
    def choice_text(self):
        for choice, choice_text in self.vote_choices:
            if self.choice == choice:
                return choice_text

    @property
    def vote_score(self):
        vote_score_dict = {
            self.OMG: 6,
            self.YES: 5,
            self.SEENOK: 4,
            self.MEH: 3,
            self.NO: 2,
            self.SEENNO: 1,
            self.VETO: 0,
        }
        return vote_score_dict[self.choice]

    def __str__(self):
        return f'{self.user}|{self.film.db.title}|{self.choice}'


class FilmComment(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)

    def __str__(self):
        return f'{self.user}|{self.film.db.title}|{self.text}'
