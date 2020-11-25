import random
import re

from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from filmdemocracy.democracy.models import Film, Club, Meeting
from filmdemocracy.democracy.models import CLUB_ID_N_DIGITS, FILM_ID_N_DIGITS


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


def add_club_context(context, club):
    context['club'] = club
    context['club_members'] = club.members.filter(is_active=True)
    context['club_admins'] = club.admin_members.filter(is_active=True)
    return context


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
