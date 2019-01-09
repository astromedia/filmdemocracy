import requests

from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.shortcuts import get_object_or_404

from filmdemocracy.democracy.models import FilmDb, Film, Vote
from filmdemocracy.socialclub.models import Club
from filmdemocracy.democracy import forms
from filmdemocracy.settings import OMDB_API_KEY


@method_decorator(login_required, name='dispatch')
class CandidateFilmsView(generic.TemplateView):
    # TODO: change to ListView?
    template_name = 'democracy/candidate_films.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        club_films = Film.objects.all().filter(club_id=club.id)
        candidate_films = []
        for film in club_films.filter(seen=False):
            film_voters = [vote.user.username for vote in film.vote_set.all()]
            candidate_films.append({
                'film': film,
                'voted': self.request.user.username in film_voters
            })
        context['candidate_films'] = candidate_films
        return context


@method_decorator(login_required, name='dispatch')
class FilmSeenSelectionView(generic.TemplateView):
    # TODO: change to ListView?
    template_name = 'democracy/film_seen_selection.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        club_films = Film.objects.all().filter(club_id=club.id)
        context['candidate_films'] = club_films.filter(seen=False)
        return context


@method_decorator(login_required, name='dispatch')
class AddNewFilmView(generic.FormView):
    form_class = forms.FilmAddNewForm
    template_name = 'democracy/add_new_film.html'

    def get_form_kwargs(self):
        kwargs = super(AddNewFilmView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'democracy:candidate_films',
            kwargs={'club_id': self.kwargs['club_id']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context

    def form_valid(self, form):
        imdb_id = form.cleaned_data['imdb_url']
        filmdb, created = FilmDb.objects.get_or_create(imdb_id=imdb_id)
        if created:
            omdb_api_url = f'http://www.omdbapi.com/?i=tt{imdb_id}' \
                f'&apikey={OMDB_API_KEY}'
            response = requests.get(omdb_api_url)
            omdb_data = response.json()
            filmdb.faff_id = form.cleaned_data['faff_url']
            filmdb.title = omdb_data['Title']
            filmdb.year = omdb_data['Year']
            filmdb.director = omdb_data['Director']
            filmdb.writer = omdb_data['Writer']
            filmdb.actors = omdb_data['Actors']
            filmdb.poster_url = omdb_data['Poster']
            filmdb.duration = int(omdb_data['Runtime'].replace('min', ''))
            filmdb.language = omdb_data['Language']
            filmdb.rated = omdb_data['Rated']
            filmdb.country = omdb_data['Country']
            filmdb.plot = omdb_data['Plot']
            filmdb.save()
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        Film.objects.create(
            id=f'{int(club.id):05d}{int(imdb_id):07d}',
            proposed_by=self.request.user,
            club=club,
            filmdb=filmdb,
        )
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class FilmDetailView(generic.TemplateView):
    model = Film
    template_name = 'democracy/film_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        film = get_object_or_404(Film, pk=self.kwargs['film_id'])
        context['film'] = film
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])

        def choice_meta(vote_choice):
            vote_meta_dict = {
                Vote.OMG: (6, 'positive'),
                Vote.YES: (5, 'positive'),
                Vote.SEENOK: (4, 'positive'),
                Vote.MEH: (3, 'neutral'),
                Vote.NO: (2, 'negative'),
                Vote.SEENNO: (1, 'negative'),
                Vote.VETO: (0, 'negative'),
            }
            return vote_meta_dict[vote_choice]

        choice_dict = {}
        for choice in Vote.vote_choices:
            choice_dict[choice[0]] = {
                'choice': choice[0],
                'choice_text': choice[1],
                'choice_rank': choice_meta(choice[0])[0],
                'choice_karma': choice_meta(choice[0])[1],
                'choice_voted': False,
            }
        try:
            user_vote = Vote.objects.get(
                user=self.request.user,
                film=film,
            )
            choice_dict[user_vote.choice]['choice_voted'] = True
        except Vote.DoesNotExist:
            pass
        context['vote_choices'] = choice_dict
        return context


def vote_film(request, club_id, film_id):
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    user_vote, _ = Vote.objects.get_or_create(
        user=request.user,
        film=film,
        club=club,
    )
    user_vote.choice = request.POST['choice']
    user_vote.save()
    return HttpResponseRedirect(
        reverse('democracy:candidate_films', kwargs={'club_id': club_id}))


@method_decorator(login_required, name='dispatch')
class FilmAddFilmAffView(generic.FormView):
    form_class = forms.FilmAddFilmAffForm
    template_name = 'democracy/film_add_faff.html'

    def get_success_url(self):
        return reverse_lazy(
            'democracy:film_detail',
            kwargs={'club_id': self.kwargs['club_id'],
                    'film_id': self.kwargs['film_id']}
        )

    def form_valid(self, form):
        imdb_id = str(self.kwargs['film_id'])[5:]
        filmdb = get_object_or_404(FilmDb, imdb_id=imdb_id)
        filmdb.faff_id = form.cleaned_data['faff_url']
        filmdb.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['film'] = get_object_or_404(Film, pk=self.kwargs['film_id'])
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context


@method_decorator(login_required, name='dispatch')
class FilmSeenView(generic.FormView):
    form_class = forms.FilmSeenForm
    template_name = 'democracy/film_seen.html'

    def get_success_url(self):
        return reverse_lazy(
            'democracy:film_detail',
            kwargs={'club_id': self.kwargs['club_id'],
                    'film_id': self.kwargs['film_id']}
        )

    def get_form_kwargs(self):
        kwargs = super(FilmSeenView, self).get_form_kwargs()
        kwargs.update({'film_id': self.kwargs['film_id']})
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_members = club.users.filter(
            is_superuser=False,
            is_active=True,
        )
        kwargs.update({'club_members': club_members})
        return kwargs

    def form_valid(self, form):
        film = get_object_or_404(Film, id=self.kwargs['film_id'])
        film.seen_date = form.cleaned_data['seen_date']
        members = form.cleaned_data['members']
        for member in members:
            film.seen_by.add(member)
        film.seen = True
        film.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['film'] = get_object_or_404(Film, pk=self.kwargs['film_id'])
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        club_members = club.users.filter(
            is_superuser=False,
            is_active=True,
        )
        context['club_members'] = club_members
        return context


def unsee_film(request, club_id, film_id):
    film = get_object_or_404(Film, pk=film_id)
    film.seen = False
    film.seen_date = None
    film.save()
    return HttpResponseRedirect(reverse_lazy(
            'democracy:film_detail',
            kwargs={'club_id': club_id,
                    'film_id': film_id}
    ))


def delete_film(request, club_id, film_id):
    film = get_object_or_404(Film, pk=film_id)
    film.delete()
    return HttpResponseRedirect(
        reverse('democracy:candidate_films', kwargs={'club_id': club_id})
    )


@method_decorator(login_required, name='dispatch')
class ParticipantsView(generic.TemplateView):
    template_name = 'democracy/participants.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        club_members = club.users.filter(
            is_superuser=False,
            is_active=True,
        )
        context['club_members'] = club_members
        return context


@method_decorator(login_required, name='dispatch')
class VoteResultsView(generic.TemplateView):
    template_name = 'democracy/vote_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        def process(film, participants):
            warnings = []
            film_all_votes = film.vote_set.all()
            film_voters = [vote.user.username for vote in film_all_votes]
            no_voters = []
            for participant in participants:
                if participant not in film_voters:
                    no_voters.append(participant)
            film_votes = []
            positive_voters = []
            negative_voters = []
            for vote in film_all_votes:
                voter = vote.user.username
                if voter in participants:
                    film_votes.append(vote.choice)
                    if vote.vote_karma is 'positive':
                        positive_voters.append(voter)
                    elif vote.vote_karma is 'negative':
                        negative_voters.append(voter)
                    if vote.choice == Vote.VETO:
                        warnings.append({
                            'type': Vote.VETO,
                            'film': film.filmdb.title,
                            'voter': voter,
                        })
                elif voter not in participants:
                    if vote.choice == Vote.OMG:
                        warnings.append({
                            'type': Vote.OMG,
                            'film': film.filmdb.title,
                            'voter': voter,
                        })
            voters_info = (positive_voters, negative_voters, no_voters)

            # TODO: use aggregations to do this count
            n_veto = film_votes.count(Vote.VETO)
            n_seenno = film_votes.count(Vote.SEENNO)
            n_no = film_votes.count(Vote.NO)
            n_meh = film_votes.count(Vote.MEH)
            n_seenok = film_votes.count(Vote.SEENOK)
            n_yes = film_votes.count(Vote.YES)
            n_omg = film_votes.count(Vote.OMG)
            if n_veto >= 1:
                return voters_info, warnings, -1000, True
            else:
                film_points = (
                        - 50 * n_seenno
                        - 25 * n_no
                        + 0 * n_meh
                        + 5 * n_seenok
                        + 10 * n_yes
                        + 20 * n_omg
                )
                return voters_info, warnings, film_points, False

        films_results = []
        films_warnings = []
        participants = self.request.GET.getlist('participants')
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_films = Film.objects.all().filter(club_id=club.id)
        for film in club_films.filter(seen=False):
            voters_info, warnings, points, veto = process(film, participants)
            films_results.append({
                'id': film.id,
                'title': film.filmdb.title,
                'positive_voters': voters_info[0],
                'negative_voters': voters_info[1],
                'no_voters': voters_info[2],
                'points': points,
                'veto': veto,
                })
            films_warnings.extend(warnings)
        context['club'] = club
        context['films_results'] = films_results
        context['warnings'] = films_warnings
        context['participants'] = participants
        return context
