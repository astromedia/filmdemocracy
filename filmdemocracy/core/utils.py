import random
import requests
from datetime import datetime, timezone
import re

from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template import loader

from filmdemocracy.core.models import Notification
from filmdemocracy.democracy.models import Film, Vote, Club, Meeting, Invitation
from filmdemocracy.chat.models import ChatUsersInfo
from filmdemocracy.democracy.models import CLUB_ID_N_DIGITS, FILM_ID_N_DIGITS
from filmdemocracy.registration.models import User
from filmdemocracy.secrets import OMDB_API_KEY


def user_is_club_member_check(user, club_id=None, club=None):
    if club is None and club_id:
        club = get_object_or_404(Club, id=club_id)
    club_members = club.members.filter(is_active=True)
    return user in club_members


def user_is_club_admin_check(user, club_id=None, club=None):
    if club is None and club_id:
        club = get_object_or_404(Club, id=club_id)
    club_members = club.members.filter(is_active=True)
    club_admins = club.admin_members.filter(is_active=True)
    return user in club_members and user in club_admins


def user_is_organizer_check(user, club_id=None, club=None, meeting_id=None):
    if club is None and club_id:
        club = get_object_or_404(Club, id=club_id)
    meeting = get_object_or_404(Meeting, id=meeting_id)
    club_members = club.members.filter(is_active=True)
    return user in club_members and user == meeting.organizer


def users_know_each_other_check(user, chat_user_id=None, chat_user=None):
    if chat_user is None and chat_user_id:
        chat_user = get_object_or_404(User, id=chat_user_id)
    common_clubs = user.club_set.all() & chat_user.club_set.all()
    chat_opened = ChatUsersInfo.objects.filter(user=user, user_known=chat_user)
    if common_clubs.exists() or chat_opened.exists():
        return True
    else:
        return False


def add_club_context(context, club):
    context['club'] = club
    context['club_members'] = club.members.filter(is_active=True)
    context['club_admins'] = club.admin_members.filter(is_active=True)
    return context


def fill_options_string(view_option=None, order_option=None, display_option=None):
    options_string = ''
    if view_option and view_option != 'all':
        options_string += f'&view={view_option}'
    if order_option and order_option != 'title':
        options_string += f'&order={order_option}'
    if display_option and display_option != 'posters':
        options_string += f'&display={display_option}'
    return options_string


def extract_options(options_string=None):
    if options_string:
        view_option = re.search(r'(&view=[0-9a-zA-Z_]+)', options_string)
        view_option = view_option.group(1) if view_option else ''
        order_option = re.search(r'(&order=[0-9a-zA-Z_]+)', options_string)
        order_option = order_option.group(1) if order_option else ''
        display_option = re.search(r'(&display=[0-9a-zA-Z_]+)', options_string)
        display_option = display_option.group(1) if display_option else ''
        return view_option, order_option, display_option
    else:
        return '', '', ''


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
        self.id = film.public_id
        self.participants = participants
        self.ranking_config = ranking_config
        self.film_votes = None
        self.film_voters = None
        self.abstentionists = None
        self.positive_votes = None
        self.neutral_votes = None
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
            self.neutral_votes = self.get_neutral_votes()
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

    def get_neutral_votes(self):
        neutral_votes = []
        for vote in self.film_votes:
            if vote.user in self.participants and vote.vote_karma is 'neutral':
                neutral_votes.append(vote)
        return neutral_votes

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
                    'film': self.film.db.title,
                    'voter': vote.user.username,
                })
        return veto_warnings

    def get_not_present_omg_warnings(self):
        not_present_omg_warnings = []
        for vote in self.film_votes:
            if vote.user not in self.participants and vote.choice == Vote.OMG:
                not_present_omg_warnings.append({
                    'type': Vote.OMG,
                    'film': self.film.db.title,
                    'voter': vote.user.username,
                })
        return not_present_omg_warnings

    def get_proposer_not_present_warning(self):
        proposer_not_present_warning = []
        if self.film.proposed_by not in self.participants:
            proposer_not_present_warning.append({
                'type': 'proposer missing',
                'film': self.film.db.title,
                'voter': self.film.proposed_by.username,
            })
        return proposer_not_present_warning

    def get_points(self):
        points_mapping = self.ranking_config['points_mapping']
        points = 0
        for vote in self.positive_votes + self.neutral_votes + self.negative_votes:
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
            if film.db.duration_in_mins_int > self.config['max_duration']:
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
                    'film': ranking_film.film,
                    'duration': str(ranking_film.film.db.duration_in_mins_int),
                    'positive_votes': ranking_film.positive_votes,
                    'neutral_votes': ranking_film.neutral_votes,
                    'negative_votes': ranking_film.negative_votes,
                    'abstentionists': ranking_film.abstentionists,
                    'points': ranking_film.points,
                    'veto': ranking_film.veto,
                    'warnings': ranking_film.warnings,
                })
        return ranking_results, self.participants


def random_club_id_generator(n_digits=CLUB_ID_N_DIGITS):
    """ Picks an integer in the [10**(n_digits-1), 10**n_digits-1] range among the free ones """
    base_ids = list(range(10**(n_digits-1), 10**n_digits - 1))
    club_ids = Club.objects.values_list('id', flat=True)
    free_ids = list(set(base_ids) - set(club_ids))
    return str(random.choice(free_ids)).zfill(n_digits)


def random_film_public_id_generator(club, n_digits=FILM_ID_N_DIGITS):
    """ Picks an integer in the [10**(n_digits-1), 10^n_digits-1] range among the free ones in the club """
    club_films = Film.objects.filter(club=club)
    base_ids = list(range(10**(n_digits-1), 10**n_digits - 1))
    films_public_ids = club_films.values_list('public_id', flat=True)
    free_ids = list(set(base_ids) - set(films_public_ids))
    return str(random.choice(free_ids)).zfill(n_digits)


class NotificationsHelper:

    def __init__(self, request=None):
        self.request = request
        self.notifications = None
        self.messages = []
        self.unread_count = 0
        self.max_notifications = 50

    def check_user_is_anonymous(self):
        return self.request.user.is_anonymous

    def build_ntf_message(self, ntf, ntf_type, ntf_ids, object_id=None, object_name=None, counter=0, image_url=None):
        ntf_message = {
            'type': ntf_type,
            'image_url': self.get_notification_image_url(ntf, ntf_type, object_id),
            'activator': ntf.activator,
            'object_id': object_id,
            'object_name': object_name,
            'counter': counter,
            'club_id': ntf.club.id if ntf.club else None,
            'club_name': ntf.club.name if ntf.club else None,
            'created_datetime': ntf.created_datetime,
            'time_ago': time_ago_format(datetime.now(timezone.utc) - ntf.created_datetime),  # TODO: use pytz
            'read': ntf.read,
            'ntf_ids': '_'.join([str(ntf_id) for ntf_id in ntf_ids]) if isinstance(ntf_ids, list) else str(ntf_ids),
        }
        return ntf_message

    def get_image_url_object_mapping(self):
        image_url_generator_mapping = {
            Notification.SIGNUP: self.get_website_image_url,
            Notification.JOINED: self.get_activator_image_url,
            Notification.JOINED + '_self': self.get_club_image_url,
            Notification.LEFT: self.get_activator_image_url,
            Notification.MEET_ORGAN: self.get_activator_image_url,
            Notification.MEET_EDIT: self.get_activator_image_url,
            Notification.MEET_DEL: self.get_activator_image_url,
            Notification.SEEN_FILM: self.get_activator_image_url,
            Notification.PROMOTED: self.get_member_image_url,
            Notification.PROMOTED + '_self': self.get_activator_image_url,
            Notification.KICKED: self.get_member_image_url,
            Notification.KICKED + '_self': self.get_activator_image_url,
            Notification.ADDED_FILM: self.get_activator_image_url,
            Notification.ADDED_FILM + 's': self.get_activator_image_url,
            Notification.COMM_FILM: self.get_activator_image_url,
            Notification.COMM_FILM + 's': self.get_film_image_url,
            Notification.COMM_COMM: self.get_activator_image_url,
            Notification.COMM_COMM + 's': self.get_film_image_url,
            Notification.ABANDONED: self.get_club_image_url,
            Notification.INVITED: self.get_club_image_url,
        }
        return image_url_generator_mapping

    def get_notification_image_url(self, ntf, ntf_type, object_id):
        image_url_generator_mapping = self.get_image_url_object_mapping()
        image_url_generator = image_url_generator_mapping[ntf_type]
        return image_url_generator(ntf, object_id)

    @staticmethod
    def get_website_image_url(ntf, object_id):
        return '/static/core/svg/web_letters.svg'

    @staticmethod
    def get_activator_image_url(ntf, object_id):
        if ntf.activator.profile_image:
            return ntf.activator.profile_image.url
        else:
            return '/static/registration/svg/user_no_profile_image.svg'

    @staticmethod
    def get_member_image_url(ntf, object_id):
        member = User.objects.get(id=object_id)
        if member.profile_image:
            return member.profile_image.url
        else:
            return '/static/registration/svg/user_no_profile_image.svg'

    @staticmethod
    def get_film_image_url(ntf, object_id):
        film = Film.objects.get(id=object_id)
        if film.db.poster_url:
            return film.db.poster_url
        else:
            return None

    @staticmethod
    def get_club_image_url(ntf, object_id):
        if ntf.club.logo_image:
            return ntf.club.logo_image.url
        else:
            return '/static/democracy/images/club_no_logo.png'

    def get_user_notifications(self):
        return Notification.objects.filter(recipient=self.request.user)

    def get_processing_mapping(self):
        processing_mapping = {
            Notification.SIGNUP: self.process_base_notifications,
            Notification.JOINED: self.process_member_notifications,
            Notification.LEFT: self.process_base_notifications,
            Notification.MEET_ORGAN: self.process_meetings_notifications,
            Notification.MEET_EDIT: self.process_meetings_notifications,
            Notification.MEET_DEL: self.process_meetings_notifications,
            Notification.SEEN_FILM: self.process_seen_films_notifications,
            Notification.PROMOTED: self.process_member_notifications,
            Notification.KICKED: self.process_member_notifications,
            Notification.ADDED_FILM: self.process_added_films_notification,
            Notification.COMM_FILM: self.process_comments_notifications,
            Notification.COMM_COMM: self.process_comments_notifications,
            Notification.ABANDONED: self.process_base_notifications,
            Notification.INVITED: self.process_invitation_notifications,
        }
        return processing_mapping

    def process_notifications(self):
        self.notifications = self.get_user_notifications()
        if self.notifications:
            processing_mapping = self.get_processing_mapping()
            for ntf_type, processing_function in processing_mapping.items():
                processing_function(ntf_type)
        self.messages = sorted(self.messages, key=lambda k: k['created_datetime'], reverse=True)[0:self.max_notifications]

    def process_base_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            if not ntf.read:
                self.unread_count += 1
            self.messages.append(self.build_ntf_message(ntf, ntf.type, ntf.id))

    def process_meetings_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            try:
                object_meeting = Meeting.objects.get(id=ntf.object_id)
                if not ntf.read:
                    self.unread_count += 1
                self.messages.append(self.build_ntf_message(ntf, ntf.type, ntf.id, object_meeting.id, object_meeting.name))
            except Meeting.DoesNotExist:
                pass

    def process_seen_films_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            try:
                object_film = Film.objects.get(id=ntf.object_id)
                if not ntf.read:
                    self.unread_count += 1
                self.messages.append(self.build_ntf_message(ntf, ntf.type, ntf.id, object_film.id, object_film.db.title))
            except Film.DoesNotExist:
                pass

    def process_member_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            try:
                object_member = User.objects.get(id=ntf.object_id)
                if not ntf.read:
                    self.unread_count += 1
                if object_member == self.request.user:
                    ntf_type = ntf.type + '_self'
                else:
                    ntf_type = ntf.type
                self.messages.append(self.build_ntf_message(ntf, ntf_type, ntf.id, object_member.id, object_member.username))
            except User.DoesNotExist:
                pass

    def process_added_films_notification(self, notification_type):
        ntfs_group = self.notifications.filter(type=notification_type).order_by('-created_datetime')
        for i, ntfs_subgroup in enumerate([ntfs_group.filter(read=True), ntfs_group.filter(read=False)]):
            ntf_activators = set(ntf.activator for ntf in ntfs_subgroup)
            for ntf_activator in ntf_activators:
                ntf_activator_group = ntfs_subgroup.filter(activator=ntf_activator.id)
                ntf_ids = [ntf.id for ntf in ntf_activator_group]
                last_ntf = ntf_activator_group.last()
                try:
                    object_film = Film.objects.get(id=last_ntf.object_id)
                    if len(ntf_activator_group) > 1:
                        counter = len(ntf_activator_group)
                        ntf_type = last_ntf.type + 's'
                    else:
                        counter = 0
                        ntf_type = last_ntf.type
                    if i == 1:
                        if not last_ntf.read:
                            self.unread_count += 1
                    self.messages.append(self.build_ntf_message(last_ntf, ntf_type, ntf_ids, object_film.id, object_film.db.title, counter))
                except Film.DoesNotExist:
                    pass

    def process_comments_notifications(self, notification_type):
        ntfs_group = self.notifications.filter(type=notification_type).order_by('-created_datetime')
        for i, ntfs_subgroup in enumerate([ntfs_group.filter(read=True), ntfs_group.filter(read=False)]):
            ntf_films = set(ntf.object_film for ntf in ntfs_subgroup)
            for ntf_film in ntf_films:
                ntf_film_group = ntfs_subgroup.filter(object_film=ntf_film.public_id)
                ntf_ids = [ntf.id for ntf in ntf_film_group]
                last_ntf = ntf_film_group.last()
                try:
                    object_film = Film.objects.get(id=last_ntf.object_id)
                    if len(ntf_film_group) > 1:
                        counter = len(ntf_film_group)
                        ntf_type = last_ntf.type + 's'
                    else:
                        counter = 0
                        ntf_type = last_ntf.type
                    if i == 1:
                        if not last_ntf.read:
                            self.unread_count += 1
                    self.messages.append(self.build_ntf_message(last_ntf, ntf_type, ntf_ids, object_film.public_id, object_film.db.title, counter))
                except Film.DoesNotExist:
                    pass

    def process_invitation_notifications(self, notification_type):
        for ntf in self.notifications.filter(type=notification_type):
            try:
                object_invitation = Invitation.objects.get(id=ntf.object_id)
                if not ntf.read:
                    self.unread_count += 1
                self.messages.append(self.build_ntf_message(ntf, ntf.type, ntf.id, object_invitation.id))
            except Invitation.DoesNotExist:
                pass

    def get_dispatch_url_mapping(self):
        processing_mapping = {
            Notification.SIGNUP: self.dispatch_url_tour,
            Notification.JOINED: self.dispatch_url_member,
            Notification.JOINED + '_self': self.dispatch_url_club,
            Notification.LEFT: self.dispatch_url_club,
            Notification.MEET_ORGAN: self.dispatch_url_club,
            Notification.MEET_EDIT: self.dispatch_url_club,
            Notification.MEET_DEL: self.dispatch_url_club,
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
            Notification.ABANDONED: self.dispatch_url_club,
            Notification.INVITED: self.dispatch_url_invitation_link,
        }
        return processing_mapping

    def get_dispatch_url(self, ntf_type, ntf_club_id, ntf_object_id):
        dispatch_url_mapping = self.get_dispatch_url_mapping()
        dispatch_url_function = dispatch_url_mapping[ntf_type]
        url = dispatch_url_function(ntf_club_id, ntf_object_id)
        return url

    @staticmethod
    def dispatch_url_home(club_id=None, ntf_object_id=None):
        return reverse('core:home')

    @staticmethod
    def dispatch_url_tour(club_id=None, ntf_object_id=None):
        return reverse('core:tour')

    @staticmethod
    def dispatch_url_member(club_id=None, ntf_object_id=None):
        return reverse('democracy:club_member_detail', kwargs={'club_id': club_id,
                                                               'member_id': ntf_object_id})

    @staticmethod
    def dispatch_url_club(club_id=None, ntf_object_id=None):
        return reverse('democracy:club_detail', kwargs={'club_id': club_id})

    @staticmethod
    def dispatch_url_film(club_id=None, ntf_object_id=None):
        film = get_object_or_404(Film, club_id=club_id, id=ntf_object_id)
        return reverse('democracy:film_detail', kwargs={'club_id': club_id,
                                                        'film_public_id': film.public_id,
                                                        'film_slug': film.db.slug})

    @staticmethod
    def dispatch_url_films(club_id=None, ntf_object_id=None):
        return reverse('democracy:candidate_films', kwargs={'club_id': club_id})

    @staticmethod
    def dispatch_url_invitation_link(club_id=None, ntf_object_id=None):
        return reverse('democracy:invite_new_member_confirm', kwargs={'invitation_id': ntf_object_id})


class SpamHelper:

    def __init__(self, request, subject_template, email_template, html_email_template):
        self.request = request
        self.use_https = self.request.is_secure()
        self.from_email = 'filmdemocracyweb@gmail.com'
        self.subject_template = subject_template
        self.email_template = email_template
        self.html_email_template = html_email_template
        self.domain_override = None
        self.default_context = self.get_default_context()

    def get_default_context(self):
        default_context = {'user': self.request.user,
                           'protocol': 'https' if self.use_https else 'http'}
        if not self.domain_override:
            current_site = get_current_site(self.request)
            default_context['current_site'] = get_current_site(self.request)
            default_context['site_name'] = current_site.name
            default_context['domain'] = current_site.domain
        else:
            default_context['site_name'] = default_context['domain'] = self.domain_override
        return default_context

    def send_emails(self, to_emails_list, email_context=None):
        context = {**self.default_context, **email_context}
        subject = loader.render_to_string(self.subject_template, context)
        subject = ''.join(subject.splitlines())  # http://nyphp.org/phundamentals/8_Preventing-Email-Header-Injection
        body = loader.render_to_string(self.email_template, context)
        for to_email in to_emails_list:
            email_messages = EmailMultiAlternatives(subject, body, self.from_email, [to_email])
            if self.html_email_template:
                html_email = loader.render_to_string(self.html_email_template, context)
                email_messages.attach_alternative(html_email, 'text/html')
            email_messages.send()


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
