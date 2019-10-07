import os
import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.urls import reverse_lazy

from filmdemocracy.registration.models import User
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify


CLUB_ID_N_DIGITS = 5
FILM_ID_N_DIGITS = 5
MEETING_ID_N_DIGITS = 4


def get_club_logo_path(instance, filename):
    return os.path.join('club_logos', str(instance.id), filename)


class Club(models.Model):
    DEFAULT_PANEL_STRING = """
    \r\n## A sample club panel written in markdown
    \r\n
    \r\n---
    \r\n
    \r\n#### Point 1: Here is some text.
    \r\nHello world, I'm a cinema club...
    \r\n
    \r\n#### Point 2: And here is a list to consider:
    \r\n1. Item #1
    \r\n2. Item #2
    \r\n3. Item #3
    \r\n
    \r\n#### Point 3: And here is an unordered list to consider:
    \r\n- Item 1
    \r\n- Item 2
    \r\n- Item 3
    """
    id = models.CharField(primary_key=True, unique=True, max_length=CLUB_ID_N_DIGITS)
    name = models.CharField(_('Club name'), max_length=50)
    created_date = models.DateField('club created date', auto_now_add=True)
    short_description = models.CharField(_('Short description (optional)'), max_length=120)
    panel = MarkdownxField(
        _('Club panel: description, rules, etc. (optional)'),
        max_length=20000,
        default=DEFAULT_PANEL_STRING,
        blank=True,
        null=True,
    )
    # TODO: Input image validation.
    logo = models.ImageField(_('club logo'), upload_to=get_club_logo_path, blank=True, null=True)
    members = models.ManyToManyField(User)
    admin_members = models.ManyToManyField(User, related_name='admin_members')

    def __str__(self):
        return f"{self.id}|{self.name}"

    @property
    def formatted_panel(self):
        return markdownify(str(self.panel))


class InvitationLink(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    invited_email = models.EmailField(max_length=254)

    def __str__(self):
        return f"{self.club}|{self.invited_email}"


class ChatClubPost(models.Model):
    user_sender = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    datetime = models.DateTimeField('comment datetime', auto_now_add=True)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)

    def __str__(self):
        return f'{self.club}|{self.user_sender}|{self.datetime}|{self.text}'


class ChatClubInfo(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    last_post = models.ForeignKey(ChatClubPost, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.club}|{self.last_post.datetime}'


class ChatUsersPost(models.Model):
    user_sender = models.ForeignKey(User, related_name='user_sender', on_delete=models.CASCADE)
    user_receiver = models.ForeignKey(User, related_name='user_receiver', on_delete=models.CASCADE)
    datetime = models.DateTimeField('comment datetime', auto_now_add=True)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)

    def __str__(self):
        return f'{self.user_sender}|{self.user_receiver}|{self.datetime}|{self.text}'


class ChatUsersInfo(models.Model):
    user = models.ForeignKey(User, related_name='chat_user', on_delete=models.CASCADE)
    user_known = models.ForeignKey(User, related_name='chat_user_known', on_delete=models.CASCADE)
    created_date = models.DateField('chat created date', auto_now_add=True)
    last_post = models.ForeignKey(ChatUsersPost, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.user}|{self.user_known}|{self.last_post.datetime}'


class ClubMemberInfo(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.member}|{self.club}'


class Meeting(models.Model):
    id = models.CharField(primary_key=True, unique=True, max_length=(CLUB_ID_N_DIGITS + MEETING_ID_N_DIGITS))
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    name = models.CharField(_('Name'), default=_('Club meeting'), max_length=50)
    description = models.CharField(_('Description (optional)'), default='', max_length=5000)
    organizer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    place = models.CharField(_('Place'), default='', max_length=100)
    date = models.DateField(_('Date'))
    time_start = models.TimeField(_('Start time (optional)'), null=True, blank=True)
    time_end = models.TimeField(_('End time (optional)'), null=True, blank=True)
    members_yes = models.ManyToManyField(User, related_name='members_yes')
    members_maybe = models.ManyToManyField(User, related_name='members_maybe')
    members_no = models.ManyToManyField(User, related_name='members_no')
    created_datetime = models.DateTimeField('meeting created datetime', auto_now_add=True)

    def __str__(self):
        return f'{self.id}|{self.name}'


class FilmDb(models.Model):
    imdb_id = models.CharField('IMDb id', primary_key=True, max_length=7)
    faff_id = models.CharField('FilmAffinity id', default='', max_length=6)
    title = models.CharField(default='', max_length=1000)
    slug = models.SlugField(unique=True)
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
    created_date = models.DateField('db created date', auto_now_add=True)
    last_updated = models.DateField('last db update date', auto_now=True)

    def save(self, *args, **kwargs):
        self.slug = self.slug or slugify(self.title)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.imdb_id}|{self.title}'

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
    def imdb_url(self):
        return f'https://www.imdb.com/title/tt{self.imdb_id}/'

    @property
    def faff_url(self):
        return f'https://www.filmaffinity.com/es/film{self.faff_id}.html'

    @property
    def updatable(self):
        time_diff_created = datetime.datetime.now().date() - self.created_date
        time_diff_updated = self.last_updated - self.created_date
        return time_diff_created > 2 * time_diff_updated


class Film(models.Model):
    """ Film proposed by user in club. Obtains info from FilmDb. """
    id = models.CharField(primary_key=True, unique=True, max_length=(CLUB_ID_N_DIGITS + FILM_ID_N_DIGITS))  # 5(club)+5
    imdb_id = models.CharField('IMDb id', max_length=7)
    proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    filmdb = models.ForeignKey(FilmDb, on_delete=models.CASCADE)
    pub_datetime = models.DateTimeField('published datetime', auto_now_add=True)
    seen = models.BooleanField(default=False)
    seen_by = models.ManyToManyField(User, related_name='seen_by')
    seen_date = models.DateField('date seen', null=True, blank=True)

    def __str__(self):
        return f'{self.id}|{self.filmdb.title}'

    @property
    def share_link(self):
        return reverse_lazy('democracy:film_detail', kwargs={'film_id': self.id, 'film_slug': self.filmdb.slug})


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
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
    choice = models.CharField(max_length=6, choices=vote_choices)

    @property
    def vote_karma(self):
        if self.choice in [self.OMG, self.YES, self.SEENOK, self.MEH]:
            return 'positive'
        elif self.choice in [self.NO, self.SEENNO, self.VETO]:
            return 'negative'

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
        return f'{self.user}|{self.film.filmdb.title}|{self.choice}'


class FilmComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    datetime = models.DateTimeField('comment datetime', auto_now_add=True)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)

    def __str__(self):
        return f'{self.user}|{self.film.filmdb.title}|{self.text}'


class Notification(models.Model):
    JOINED = 'joined'
    PROMOTED = 'promoted'
    LEFT = 'left'
    ADDED_FILM = 'addedfilm'
    SEEN_FILM = 'seenfilm'
    ORGAN_MEET = 'organmeet'
    COMM_FILM = 'commfilm'
    COMM_COMM = 'commcomm'
    KICKED = 'kicked'
    notification_choices = (
        (JOINED, 'Member joined the club'),
        (PROMOTED, 'Member promoted to admin.'),
        (LEFT, "Member left the club."),
        (ADDED_FILM, 'Member added new film.'),
        (SEEN_FILM, "Member marked film as seen by club."),
        (ORGAN_MEET, "Member organized a new club meeting."),
        (COMM_FILM, "Member commented in film proposed by user."),
        (COMM_COMM, 'Member commented in film commented by user.'),
        (KICKED, 'Member kicked other member from club.'),
    )
    type = models.CharField(max_length=9, choices=notification_choices)
    activator = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='active_member')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='club')
    object_member = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='passive_member')
    object_film = models.ForeignKey(Film, on_delete=models.CASCADE, null=True, related_name='passive_film')
    object_meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, null=True, related_name='passive_meeting')
    datetime = models.DateTimeField('notification datetime', auto_now_add=True)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipient')
    read = models.BooleanField('notification read', default=False)

    def __str__(self):
        return f"{self.activator.username}|{self.club}|{self.type}|{self.datetime}|{self.recipient.username}"
