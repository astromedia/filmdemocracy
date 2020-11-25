from filmdemocracy.democracy.models import Vote


class RankingFilm:
    """ Helping class to process each film in the generate_ranking method of the RankingAlgorithm class """

    def __init__(self, film, participants, ranking_config):
        self.film = film
        self.id = film.public_id
        self.participants = participants
        self.ranking_config = ranking_config
        self.film_votes = None
        self.film_voters = []
        self.abstentionists = []
        self.positive_votes = []
        self.neutral_votes = []
        self.negative_votes = []
        self.veto = False
        self.points = 0
        self.warnings = []

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
            if vote.user in self.participants and vote.vote_karma == 'positive':
                positive_votes.append(vote)
        return positive_votes

    def get_neutral_votes(self):
        neutral_votes = []
        for vote in self.film_votes:
            if vote.user in self.participants and vote.vote_karma == 'neutral':
                neutral_votes.append(vote)
        return neutral_votes

    def get_negative_votes(self):
        negative_votes = []
        for vote in self.film_votes:
            if vote.user in self.participants and vote.vote_karma == 'negative':
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