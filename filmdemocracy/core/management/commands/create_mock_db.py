import json
import glob
import os
from pprint import pprint
import ntpath
import random

from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.core.utils import random_club_id_generator, random_film_public_id_generator
from filmdemocracy.registration.models import User
from filmdemocracy.democracy import forms
from filmdemocracy.core.models import Notification
from filmdemocracy.democracy.models import Club, ClubMemberInfo, Invitation, Meeting, FilmDb, Film, Vote, FilmComment
from filmdemocracy.chat.models import ChatClubInfo


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
        self.stdout.write(f'  OK')

    def add_films_to_club(self, club):
        self.stdout.write(f'  Adding films to club: {club.name}')
        filmsdbs = FilmDb.objects.all()
        club_members = club.members.filter(is_active=True)
        for filmdb in filmsdbs:
            Film.objects.create(
                public_id=random_film_public_id_generator(club),
                proposed_by=random.choice(club_members),
                club=club,
                db=filmdb,
            )
        self.stdout.write(f'  OK')

    def create_clubs(self):
        self.stdout.write(f'  Creating clubs...')
        user_creators = [
            User.objects.filter(email='pablo@gmail.com')[0],
            User.objects.filter(email='ricardo@gmail.com')[0],
        ]

        lore_100 = "Lorem ipsum dolor sit amet consectetur adipiscing elit, praesent sem sed tristique tincidunt sociis."
        for i, club_name in enumerate(CLUB_NAMES):
            club = Club.objects.create(
                id=random_club_id_generator(),
                name=CLUB_NAMES[i],
                short_description=lore_100,
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
            self.add_films_to_club(club)
        self.stdout.write(f'  OK')

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        if not self.test_mock_exists():
            self.stdout.write(f'Creating mock db...')
            self.create_users()
            self.create_clubs()
            self.stdout.write(f'  OK')
