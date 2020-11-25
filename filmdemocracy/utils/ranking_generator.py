from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from filmdemocracy.democracy.models import Film, Vote
from filmdemocracy.registration.models import User
from filmdemocracy.utils.ranking_film import RankingFilm


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
            Vote.VETO: -100,
            Vote.SEENNO: -30,
            Vote.NO: -15,
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
