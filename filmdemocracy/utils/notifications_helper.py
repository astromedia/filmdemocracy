from datetime import datetime, timezone

from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static

from filmdemocracy.core.models import Notification
from filmdemocracy.democracy.models import Film, Meeting, Invitation
from filmdemocracy.registration.models import User
from filmdemocracy.utils.utils import time_ago_format


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
        return static('core/svg/web_letters_negative.svg')

    @staticmethod
    def get_activator_image_url(ntf, object_id):
        if ntf.activator.profile_image:
            return ntf.activator.profile_image.url
        else:
            return static('registration/svg/user_no_profile_image.svg')

    @staticmethod
    def get_member_image_url(ntf, object_id):
        member = User.objects.get(id=object_id)
        if member.profile_image:
            return member.profile_image.url
        else:
            return static('registration/svg/user_no_profile_image.svg')

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
            return static('democracy/images/club_no_logo.png')

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
    def dispatch_url_home(**kwargs):
        return reverse('core:home')

    @staticmethod
    def dispatch_url_tour(**kwargs):
        return reverse('core:tour')

    @staticmethod
    def dispatch_url_member(**kwargs):
        return reverse('democracy:club_member_detail', kwargs={'club_id': kwargs['club_id'],
                                                               'member_id': kwargs['ntf_object_id']})

    @staticmethod
    def dispatch_url_club(**kwargs):
        return reverse('democracy:club_detail', kwargs={'club_id': kwargs['club_id']})

    @staticmethod
    def dispatch_url_film(**kwargs):
        film = get_object_or_404(Film, club_id=kwargs['club_id'], id=kwargs['ntf_object_id'])
        return reverse('democracy:film_detail', kwargs={'club_id': kwargs['club_id'],
                                                        'film_public_id': film.public_id,
                                                        'film_slug': film.db.slug})

    @staticmethod
    def dispatch_url_films(**kwargs):
        return reverse('democracy:candidate_films', kwargs={'club_id': kwargs['club_id']})

    @staticmethod
    def dispatch_url_invitation_link(**kwargs):
        return reverse('democracy:invite_new_member_confirm', kwargs={'invitation_id': kwargs['ntf_object_id']})
