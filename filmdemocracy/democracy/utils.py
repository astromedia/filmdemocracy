import random
import requests
from datetime import datetime, timezone

from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from filmdemocracy.democracy.models import Film, Vote, Club, Notification, ChatUsersInfo, Meeting
from filmdemocracy.registration.models import User
from filmdemocracy.secrets import OMDB_API_KEY


def user_is_club_member_check(request, club_id):
    user = request.user
    club = get_object_or_404(Club, pk=club_id)
    club_members = club.members.filter(is_active=True)
    return user in club_members


def user_is_club_admin_check(request, club_id):
    user = request.user
    club = get_object_or_404(Club, pk=club_id)
    club_members = club.members.filter(is_active=True)
    club_admins = club.admin_members.filter(is_active=True)
    return user in club_members and user in club_admins


def user_is_organizer_check(request, club_id, meeting_id):
    user = request.user
    club = get_object_or_404(Club, pk=club_id)
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    club_members = club.members.filter(is_active=True)
    return user in club_members and user == meeting.organizer


def users_know_each_other_check(request, chatuser_id):
    user = request.user
    chat_user = get_object_or_404(User, pk=chatuser_id)
    common_clubs = user.club_set.all() & chat_user.club_set.all()
    chat_opened = ChatUsersInfo.objects.filter(user=user, user_known=chat_user)
    if common_clubs.exists() or chat_opened.exists():
        return True
    else:
        return False


def add_club_context(request, context, club_id):
    club = get_object_or_404(Club, pk=club_id)
    context['club'] = club
    context['club_members'] = club.members.filter(is_active=True)
    context['club_admins'] = club.admin_members.filter(is_active=True)
    context['user'] = request.user
    return context


def update_filmdb_omdb_info(filmdb):
    """ Returns True if the database has been updated, and False otherwise """
    omdb_api_url = f'http://www.omdbapi.com/?i=tt{filmdb.imdb_id}&plot=full&apikey={OMDB_API_KEY}'
    response = requests.get(omdb_api_url)
    if response.status_code == requests.codes.ok:
        try:
            omdb_data = response.json()
            filmdb.title = omdb_data['Title']
            filmdb.year = int(omdb_data['Year'][0:4])
            filmdb.director = omdb_data['Director']
            filmdb.writer = omdb_data['Writer']
            filmdb.actors = omdb_data['Actors']
            filmdb.poster_url = omdb_data['Poster']
            if ' min' in omdb_data['Runtime']:
                filmdb.duration = omdb_data['Runtime'].replace(' min', '')
            elif 'min' in omdb_data['Runtime']:
                filmdb.duration = omdb_data['Runtime'].replace('min', '')
            else:
                filmdb.duration = omdb_data['Runtime']
            filmdb.language = omdb_data['Language']
            filmdb.rated = omdb_data['Rated']
            filmdb.country = omdb_data['Country']
            filmdb.plot = omdb_data['Plot']
            filmdb.save()
        except KeyError:
            return False
        return True
    else:
        return False


class RankingFilm:
    """ Helping class to process each film in the generate_ranking method of the RankingAlgorithm class """

    def __init__(self, film, participants, ranking_config):
        self.film = film
        self.id = film.id
        self.filmdb = film.filmdb
        self.participants = participants
        self.ranking_config = ranking_config
        self.film_votes = None
        self.film_voters = None
        self.abstentionists = None
        self.positive_votes = None
        self.negative_votes = None
        self.veto = False
        self.points = None
        self.warnings = None

    def process_votes(self):
        self.film_votes = self.film.vote_set.all()
        if self.film_votes:
            self.film_voters = [vote.user for vote in self.film_votes]
            self.abstentionists = self.get_abstentionists()
            self.positive_votes = self.get_positive_votes()
            self.negative_votes = self.get_negative_votes()
            self.veto = self.veto_test()
            self.points = self.get_points()
            self.warnings = self.get_warnings()

    def get_abstentionists(self):
        abstentionists = []
        for participant in self.participants:
            if participant not in self.film_voters:
                abstentionists.append(participant)
        return abstentionists

    def get_positive_votes(self):
        positive_votes = []
        for vote in self.film_votes:
            if vote.user in self.participants and vote.vote_karma is 'positive':
                positive_votes.append(vote)
        return positive_votes

    def get_negative_votes(self):
        negative_votes = []
        for vote in self.film_votes:
            if vote.user in self.participants and vote.vote_karma is 'negative':
                negative_votes.append(vote)
        return negative_votes

    def veto_test(self):
        for vote in self.negative_votes:
            if vote.choice == Vote.VETO:
                return True
        return False

    def get_veto_warnings(self):
        veto_warnings = []
        for vote in self.negative_votes:
            if vote.choice == Vote.VETO:
                veto_warnings.append({
                    'type': Vote.VETO,
                    'film': self.film.filmdb.title,
                    'voter': vote.user.username,
                })
        return veto_warnings

    def get_not_present_omg_warnings(self):
        not_present_omg_warnings = []
        for vote in self.film_votes:
            if vote.user not in self.participants and vote.choice == Vote.OMG:
                not_present_omg_warnings.append({
                    'type': Vote.OMG,
                    'film': self.film.filmdb.title,
                    'voter': vote.user.username,
                })
        return not_present_omg_warnings

    def get_proposer_not_present_warning(self):
        proposer_not_present_warning = []
        if self.film.proposed_by not in self.participants:
            proposer_not_present_warning.append({
                'type': 'proposer missing',
                'film': self.film.filmdb.title,
                'voter': self.film.proposed_by.username,
            })
        return proposer_not_present_warning

    def get_points(self):
        points_mapping = self.ranking_config['points_mapping']
        points = 0
        for vote in self.positive_votes + self.negative_votes:
            points += points_mapping[vote.choice]
        return points

    def get_warnings(self):
        warnings = []
        warnings_generators = [
            self.get_veto_warnings,
            self.get_not_present_omg_warnings,
            self.get_proposer_not_present_warning,
        ]
        for warnings_generator in warnings_generators:
            warnings += warnings_generator()
        return warnings


class RankingGenerator:
    """ The algorithm to produce the film ranking """

    def __init__(self, request, club_id):
        self.request = request
        self.club_id = club_id
        self.participants = None
        self.config = {}

    @staticmethod
    def get_points_mapping():
        points_mapping = {
            Vote.VETO: -10000,
            Vote.SEENNO: -50,
            Vote.NO: -25,
            Vote.MEH: 0,
            Vote.SEENOK: +5,
            Vote.YES: +10,
            Vote.OMG: +20,
        }
        return points_mapping

    def init_config(self):
        self.config['points_mapping'] = self.get_points_mapping()
        self.config['exclude_not_present'] = self.request.GET.get('exclude_not_present')
        max_duration_input = self.request.GET.get('max_duration')
        if max_duration_input == '':
            self.config['max_duration'] = 999
        else:
            try:
                self.config['max_duration'] = int(max_duration_input)
            except ValueError:
                messages.error(self.request, _('Invalid maximum film duration input! Filter not applied.'))
                self.config['max_duration'] = 999

    def include_film_in_ranking_check(self, film):
        if film.proposed_by not in self.participants and self.config['exclude_not_present']:
            return False
        else:
            film_duration = get_film_duration_in_mins(film)
            if isinstance(film_duration, int) and film_duration > self.config['max_duration']:
                return False
            else:
                return True

    def generate_ranking(self):
        ranking_results = []
        self.init_config()
        self.participants = [get_object_or_404(User, id=mid) for mid in self.request.GET.getlist('members')]
        club_films = Film.objects.filter(club_id=self.club_id, seen=False)
        for film in club_films:
            if self.include_film_in_ranking_check(film):
                ranking_film = RankingFilm(film, self.participants, self.config)
                ranking_film.process_votes()
                ranking_results.append({
                    'id': ranking_film.id,
                    'title': ranking_film.filmdb.title,
                    'duration': f'{get_film_duration_in_mins(ranking_film.film)} min',
                    'positive_votes': ranking_film.positive_votes,
                    'negative_votes': ranking_film.negative_votes,
                    'abstentionists': ranking_film.abstentionists,
                    'points': ranking_film.points,
                    'veto': ranking_film.veto,
                    'warnings': ranking_film.warnings,
                })
        return ranking_results, self.participants


def get_film_duration_in_mins(film):
    """ Util to safely obtain the film duration in minutes (int) """
    try:
        film_duration = int(film.filmdb.duration)
    except ValueError:
        if ' min' in film.filmdb.duration:
            film_duration = int(film.filmdb.duration.replace(' min', ''))
        elif 'min' in film.filmdb.duration:
            film_duration = int(film.filmdb.duration.replace('min', ''))
        else:
            film_duration = 0
    return film_duration


def random_club_id_generator(n_digits=5):
    """ Picks an integer in the [1, 10^n_digits-1] range among the free ones (i.e., not found in the DB) """
    club_ids = Club.objects.values_list('id', flat=True)
    free_ids = [i for i in range(1, 10**n_digits - 1) if i not in club_ids]
    return str(random.choice(free_ids)).zfill(n_digits)


def random_film_id_generator(club_id, n_digits=5):
    """ Picks an integer in the [1, 10^n_digits-1] range among the free ones (i.e., not found in the DB) """
    club_films = Film.objects.filter(club_id=club_id)
    films_ids = [fid[-n_digits:] for fid in club_films.values_list('id', flat=True)]
    free_ids = [i for i in range(1, 10**n_digits - 1) if i not in films_ids]
    return str(random.choice(free_ids)).zfill(n_digits)


def random_meeting_id_generator(club_id, n_digits=4):
    """ Picks an integer in the [1, 10^n_digits-1] range among the free ones (i.e., not found in the DB) """
    club_meetings = Meeting.objects.filter(club_id=club_id)
    meetings_ids = [mid[-n_digits:] for mid in club_meetings.values_list('id', flat=True)]
    free_ids = [i for i in range(1, 10**n_digits - 1) if i not in meetings_ids]
    return str(random.choice(free_ids)).zfill(n_digits)


class NotificationsHelper:

    def __init__(self, request=None):
        self.request = request
        self.notifications = None
        self.messages = []
        self.unread_count = 0
        self.max_notifications = 20

    def check_user_is_anonymous(self):
        return self.request.user.is_anonymous

    @staticmethod
    def build_ntf_message(ntf, ntf_type, ntf_ids, object_name=None, object_id=None, counter=0):
        ntf_message = {
            'type': ntf_type,
            'activator': ntf.activator,
            'object_name': object_name,
            'object_id': object_id,
            'counter': counter,
            'club': ntf.club,
            'datetime': ntf.datetime,
            'time_ago': time_ago_format(datetime.now(timezone.utc) - ntf.datetime),  # TODO: use pytz
            'read': ntf.read,
            'ids': '_'.join(ntf_ids) if isinstance(ntf_ids, list) else str(ntf_ids),
        }
        return ntf_message

    def get_user_notifications(self):
        return Notification.objects.filter(recipient=self.request.user)

    def get_processing_mapping(self):
        processing_mapping = {
            Notification.JOINED: self.process_joined_notifications,
            Notification.LEFT: self.process_club_notifications,
            Notification.ORGAN_MEET: self.process_club_notifications,
            Notification.SEEN_FILM: self.process_seen_films_notifications,
            Notification.PROMOTED: self.process_hierarchy_notifications,
            Notification.KICKED: self.process_hierarchy_notifications,
            Notification.ADDED_FILM: self.process_added_films_notification,
            Notification.COMM_FILM: self.process_comments_notifications,
            Notification.COMM_COMM: self.process_comments_notifications,
        }
        return processing_mapping

    def get_dispatch_url_mapping(self):
        processing_mapping = {
            Notification.JOINED: self.dispatch_url_member,
            Notification.LEFT: self.dispatch_url_club,
            Notification.ORGAN_MEET: self.dispatch_url_club,
            Notification.SEEN_FILM: self.dispatch_url_film,
            Notification.PROMOTED: self.dispatch_url_member,
            Notification.PROMOTED + '_self': self.dispatch_url_member,
            Notification.KICKED: self.dispatch_url_club,
            Notification.KICKED + '_self': self.dispatch_url_home,
            Notification.ADDED_FILM: self.dispatch_url_film,
            Notification.ADDED_FILM + 's': self.dispatch_url_films,
            Notification.COMM_FILM: self.dispatch_url_film,
            Notification.COMM_FILM + 's': self.dispatch_url_film,
            Notification.COMM_COMM: self.dispatch_url_film,
            Notification.COMM_COMM + 's': self.dispatch_url_film,
        }
        return processing_mapping

    def process_notifications(self):
        self.notifications = self.get_user_notifications()
        if self.notifications:
            processing_mapping = self.get_processing_mapping()
            for ntf_type, processing_function in processing_mapping.items():
                processing_function(ntf_type)
        self.messages = sorted(self.messages, key=lambda k: k['datetime'], reverse=True)[0:self.max_notifications]

    def get_dispatch_url(self, ntf_type, ntf_club_id, ntf_object_id):
        dispatch_url_mapping = self.get_dispatch_url_mapping()
        dispatch_url_function = dispatch_url_mapping[ntf_type]
        url = dispatch_url_function(ntf_club_id, ntf_object_id)
        return url

    def process_joined_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            if not ntf.read:
                self.unread_count += 1
            self.messages.append(self.build_ntf_message(ntf, ntf.type, ntf.id, ntf.activator.username, ntf.activator.id))

    def process_club_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            if not ntf.read:
                self.unread_count += 1
            self.messages.append(self.build_ntf_message(ntf, ntf.type, ntf.id))

    def process_seen_films_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            if not ntf.read:
                self.unread_count += 1
            self.messages.append(self.build_ntf_message(ntf, ntf.type, ntf.id, ntf.object_film.filmdb.title, ntf.object_film.id))

    def process_hierarchy_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            if not ntf.read:
                self.unread_count += 1
            if ntf.object_member == self.request.user:
                ntf_type = ntf.type + '_self'
            else:
                ntf_type = ntf.type
            self.messages.append(self.build_ntf_message(ntf, ntf_type, ntf.id, ntf.object_member.username, ntf.object_member.id))

    def process_added_films_notification(self, notification_type):
        ntfs_group = self.notifications.filter(type=notification_type).order_by('-datetime')
        for i, ntfs_subgroup in enumerate([ntfs_group.filter(read=True), ntfs_group.filter(read=False)]):
            ntf_activators = set(ntf.activator for ntf in ntfs_subgroup)
            for ntf_activator in ntf_activators:
                ntf_activator_group = ntfs_subgroup.filter(activator=ntf_activator.id)
                ntf_ids = [str(ntf.id) for ntf in ntf_activator_group]
                last_ntf = ntf_activator_group.last()
                if len(ntf_activator_group) > 1:
                    counter = len(ntf_activator_group)
                    ntf_type = last_ntf.type + 's'
                else:
                    counter = 0
                    ntf_type = last_ntf.type
                if i == 1:
                    if not last_ntf.read:
                        self.unread_count += 1
                self.messages.append(self.build_ntf_message(last_ntf, ntf_type, ntf_ids, last_ntf.object_film.filmdb.title, last_ntf.object_film.id, counter))

    def process_comments_notifications(self, notification_type):
        ntfs_group = self.notifications.filter(type=notification_type).order_by('-datetime')
        for i, ntfs_subgroup in enumerate([ntfs_group.filter(read=True), ntfs_group.filter(read=False)]):
            ntf_films = set(ntf.object_film for ntf in ntfs_subgroup)
            for ntf_film in ntf_films:
                ntf_film_group = ntfs_subgroup.filter(object_film=ntf_film.id)
                ntf_ids = [str(ntf.id) for ntf in ntf_film_group]
                last_ntf = ntf_film_group.last()
                if len(ntf_film_group) > 1:
                    counter = len(ntf_film_group)
                    ntf_type = last_ntf.type + 's'
                else:
                    counter = 0
                    ntf_type = last_ntf.type
                if i == 1:
                    if not last_ntf.read:
                        self.unread_count += 1
                self.messages.append(self.build_ntf_message(last_ntf, ntf_type, ntf_ids, last_ntf.object_film.filmdb.title, last_ntf.object_film.id, counter))

    @staticmethod
    def dispatch_url_home(club_id=None, ntf_object_id=None):
        return reverse('democracy:home')

    @staticmethod
    def dispatch_url_member(club_id=None, ntf_object_id=None):
        return reverse('democracy:club_member_detail', kwargs={'club_id': club_id,
                                                               'user_id': ntf_object_id})

    @staticmethod
    def dispatch_url_club(club_id=None, ntf_object_id=None):
        return reverse('democracy:club_detail', kwargs={'club_id': club_id})

    @staticmethod
    def dispatch_url_film(club_id=None, ntf_object_id=None):
        return reverse('democracy:film_detail', kwargs={'club_id': club_id,
                                                        'film_id': ntf_object_id,
                                                        'view_option': 'all',
                                                        'order_option': 'title',
                                                        'display_option': 'posters'})

    @staticmethod
    def dispatch_url_films(club_id=None, ntf_object_id=None):
        return reverse('democracy:candidate_films', kwargs={'club_id': club_id,
                                                            'view_option': 'all',
                                                            'order_option': 'title',
                                                            'display_option': 'posters'})


def time_ago_format(datetime_diff):
    seconds = int(datetime_diff.total_seconds())
    periods = [
        (_('year'),   60*60*24*365),
        (_('day'),    60*60*24),
        (_('hour'),   60*60),
        (_('minute'), 60),
        (_('second'), 1)
    ]
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value = int(seconds / period_seconds)
            has_s = 's' if period_value > 1 else ''
            return "{} {}{}".format(period_value, period_name, has_s)
