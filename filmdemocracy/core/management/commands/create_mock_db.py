import json
import glob
import os
from pprint import pprint
import ntpath
import random
import datetime

from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.core.utils import random_club_id_generator, random_film_public_id_generator
from filmdemocracy.registration.models import User
from filmdemocracy.democracy import forms
from filmdemocracy.core.models import Notification
from filmdemocracy.democracy.models import Club, ClubMemberInfo, Invitation, Meeting, FilmDb, Film, Vote, FilmComment
from filmdemocracy.chat.models import ChatClubInfo


LORE_100 = "Lorem ipsum dolor sit amet consectetur adipiscing elit, praesent sem sed tristique tincidunt sociis."


USER_NAMES = [
    'Pablo',
    'Ricardo',
    'Alba',
    'Marcos',
    'Marta',
    'Naranjo',
    'Timi',
    'Carla',
    'Txan',
    'Juanra',
    'Andrea',
    'Diego',
    'Cris',
    'Javi',
    'Jose',
    'Pedro',
    'Elias',
    'Vega',
    'Paco',
]

CLUB_NAMES = [
    'Club de Cine de Monóculo',
    'Trabajo',
]


class Command(BaseCommand):
    help = 'Create a mock db for testing'

    @staticmethod
    def test_mock_exists():
        club = Club.objects.filter(name=CLUB_NAMES[0])
        if club:
            return True
        else:
            return False

    def create_users(self):
        self.stdout.write(f'  Creating users...')
        for name in USER_NAMES:
            User.objects.create_user(name, f'{name.lower()}@gmail.com', 'pass')

    @staticmethod
    def add_films_to_club(club):
        filmsdbs = FilmDb.objects.all()
        club_members = club.members.filter(is_active=True)
        for filmdb in filmsdbs:
            if random.random() < 0.8:
                random_member = random.choice(club_members)
                film = Film.objects.create(
                    public_id=random_film_public_id_generator(club),
                    proposed_by=random_member,
                    club=club,
                    db=filmdb,
                )
                notif_members = club.members.filter(is_active=True).exclude(id=random_member.id)
                for notif_member in notif_members:
                    Notification.objects.create(type=Notification.ADDED_FILM,
                                                activator=random_member,
                                                club=club,
                                                object_id=film.id,
                                                recipient=notif_member)

    @staticmethod
    def create_random_votes_for_films(club):
        club_members = club.members.filter(is_active=True)
        for film in club.film_set.all():
            for member in club_members:
                if random.random() < 0.8:
                    Vote.objects.create(
                        user=member,
                        film=film,
                        club=club,
                        choice=random.choice([Vote.OMG, Vote.YES, Vote.SEENOK, Vote.MEH, Vote.NO, Vote.SEENNO, Vote.VETO])
                    )

    @staticmethod
    def add_meetings_to_club(club):
        club_members = club.members.filter(is_active=True)
        counter = 0
        for i, organizer in enumerate(club_members):
            if random.random() < 0.6:
                counter += 1
                meeting = Meeting.objects.create(
                    club=club,
                    name=f'Test club amazing meeting #{counter}',
                    description=LORE_100,
                    organizer=organizer,
                    place=f'My house at #{counter} street',
                    date=datetime.date.today() + datetime.timedelta(weeks=(10+i)),
                    time_start=datetime.time(12+i, 10+i),
                )
                notif_members = club.members.filter(is_active=True).exclude(id=organizer.id)
                for notif_member in notif_members:
                    Notification.objects.create(type=Notification.ADDED_FILM,
                                                activator=organizer,
                                                club=club,
                                                object_id=meeting.id,
                                                recipient=notif_member)

    @staticmethod
    def add_random_asistance_to_meetings(club):
        club_meetings = Meeting.objects.filter(club=club, active=True, date__gte=timezone.now().date())
        club_members = club.members.filter(is_active=True)
        for meeting in club_meetings:
            for member in club_members:
                random_number = random.random()
                if 0 < random_number < 0.2:
                    meeting.members_yes.add(member)
                if 0.2 <= random_number < 0.4:
                    meeting.members_maybe.add(member)
                if 0.4 <= random_number < 0.6:
                    meeting.members_no.add(member)
                if random_number >= 0.6:
                    pass
            meeting.save()

    @staticmethod
    def mark_random_films_as_seen(club):
        club_members = club.members.filter(is_active=True)
        for film in club.film_set.all():
            if random.random() < 0.2:
                random_member = random.choice(club_members)
                film.seen_date = datetime.date.today()
                for member in club_members:
                    if random.random() < 0.5:
                        film.seen_by.add(member)
                film.seen = True
                film.marked_seen_by = random_member
                film.save()
                notif_members = club.members.filter(is_active=True).exclude(id=random_member.id)
                for notif_member in notif_members:
                    Notification.objects.create(type=Notification.SEEN_FILM,
                                                activator=random_member,
                                                club=club,
                                                recipient=notif_member,
                                                object_id=film.id)

    def create_clubs(self):
        self.stdout.write(f'  Creating clubs...')
        user_creators = [
            User.objects.filter(email='pablo@gmail.com')[0],
            User.objects.filter(email='ricardo@gmail.com')[0],
        ]

        for i, club_name in enumerate(CLUB_NAMES):
            self.stdout.write(f'  Creating club: {club_name}')
            club = Club.objects.create(
                id=random_club_id_generator(),
                founder=user_creators[i],
                name=CLUB_NAMES[i],
                short_description=LORE_100,
            )
            club.admin_members.add(user_creators[i])
            club.members.add(user_creators[0])
            ClubMemberInfo.objects.create(club=club, member=user_creators[0])
            club.members.add(user_creators[1])
            ClubMemberInfo.objects.create(club=club, member=user_creators[1])
            ChatClubInfo.objects.create(club=club)
            for name in random.sample(USER_NAMES[2:], 6):
                user = User.objects.filter(email=f'{name.lower()}@gmail.com')[0]
                club.members.add(user)
                ClubMemberInfo.objects.create(club=club, member=user)
            club.save()
            self.stdout.write(f'  Adding films to club: {club.name}')
            self.add_films_to_club(club)
            self.stdout.write(f'  Adding random votes to films in club: {club.name}')
            self.create_random_votes_for_films(club)
            self.stdout.write(f'  Marking random films as seen in club: {club.name}')
            self.mark_random_films_as_seen(club)
            self.stdout.write(f'  Adding meetings in club: {club.name}')
            self.add_meetings_to_club(club)
            self.stdout.write(f'  Adding random assistance to meetings in club: {club.name}')
            self.add_random_asistance_to_meetings(club)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        if not self.test_mock_exists():
            self.stdout.write(f'Creating mock db...')
            self.create_users()
            self.create_clubs()
            self.stdout.write(f'  OK')
