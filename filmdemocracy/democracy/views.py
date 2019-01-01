import random
import requests

from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.shortcuts import get_object_or_404
from filmdemocracy.registration.models import User

from filmdemocracy.democracy.forms import FilmAddNewForm, FilmAddFilmAffForm
from filmdemocracy.democracy.forms import FilmSeenForm
from filmdemocracy.democracy.models import Film, Vote
from filmdemocracy.settings import OMDB_API_KEY


@method_decorator(login_required, name='dispatch')
class CandidateFilmsView(generic.TemplateView):
    template_name = 'democracy/candidate_films.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        films = Film.objects.all().order_by('title')
        list_of_films = []
        for film in films:
            film_voters = [vote.user.username for vote in film.vote_set.all()]
            list_of_films.append({
                'film': film,
                'voted': self.request.user.username in film_voters
            })
        context['list_of_films'] = list_of_films
        context['last_proposed_films'] = Film.objects.all().order_by('-pub_date')
        context['last_seen_films'] = Film.objects.all().order_by('-seen_date')
        return context


@method_decorator(login_required, name='dispatch')
class AddNewFilmView(generic.FormView):
    form_class = FilmAddNewForm
    template_name = 'democracy/add_new_film.html'

    def get_success_url(self):
        return reverse('democracy:candidate_films')

    @staticmethod
    def random_id_generator():
        """
        Random id generator, that picks an integer in the [1, 999999] range
        among the free ones (i.e., not found in the DB).
        return: new_id: new id number not existing in the database
        """
        if len(Film.objects.all()) == 999999:
            raise Exception('All possible id numbers are picked!')
        else:
            filmids = Film.objects.values_list('id')
            free_ids = [i for i in range(1, 999999) if i not in filmids]
            new_id = random.choice(free_ids)
        return new_id

    def form_valid(self, form):
        new_id = self.random_id_generator()
        imdb_id = form.cleaned_data['imdb_url']
        omdb_api_url = f'http://www.omdbapi.com/?i={imdb_id}' \
            f'&apikey={OMDB_API_KEY}'
        response = requests.get(omdb_api_url)
        omdb_data = response.json()
        Film.objects.create(
            id=new_id,
            imdb_id=imdb_id,
            faff_id=form.cleaned_data['faff_url'],
            proposed_by=self.request.user,
            title=omdb_data['Title'],
            director=omdb_data['Director'],
            writer=omdb_data['Writer'],
            actors=omdb_data['Actors'],
            poster_url=omdb_data['Poster'],
            year=omdb_data['Year'],
            duration=int(omdb_data['Runtime'].replace('min', '')),
            language=omdb_data['Language'],
            rated=omdb_data['Rated'],
            country=omdb_data['Country'],
            plot=omdb_data['Plot'],
        )
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class FilmDetailView(generic.DetailView):
    model = Film
    template_name = 'democracy/film_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

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
            user_vote = Vote.objects.get(user=self.request.user,
                                         film=self.kwargs['pk'])
            choice_dict[user_vote.choice]['choice_voted'] = True
        except Vote.DoesNotExist:
            pass
        context['vote_choices'] = choice_dict
        return context


def vote_film(request, film_id):
    film = get_object_or_404(Film, pk=film_id)
    user_vote, _ = Vote.objects.get_or_create(
        user=request.user,
        film=film,
    )
    user_vote.choice = request.POST['choice']
    user_vote.save()
    return HttpResponseRedirect(reverse('democracy:candidate_films'))


@method_decorator(login_required, name='dispatch')
class FilmAddFilmAffView(generic.UpdateView):
    model = Film
    form_class = FilmAddFilmAffForm
    template_name = 'democracy/film_add_faff.html'
    success_url = reverse_lazy('democracy:candidate_films')

    def form_valid(self, form):
        form.instance.faff_id = form.cleaned_data['faff_url']
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class FilmSeenView(generic.UpdateView):
    model = Film
    form_class = FilmSeenForm
    template_name = 'democracy/film_seen.html'
    success_url = reverse_lazy('democracy:candidate_films')

    def form_valid(self, form):
        form.instance.seen = True
        return super().form_valid(form)


def unsee_film(request, film_id):
    film = get_object_or_404(Film, pk=film_id)
    film.seen = False
    film.seen_date = None
    film.save()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail', kwargs={'pk': film_id}))


def delete_film(request, film_id):
    film = get_object_or_404(Film, pk=film_id)
    film.delete()
    return HttpResponseRedirect(reverse('democracy:candidate_films'))


@method_decorator(login_required, name='dispatch')
class ParticipantsView(generic.TemplateView):
    template_name = 'democracy/participants.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_users = User.objects.filter(
            is_superuser=False,
            is_active=True,
        )
        context['all_users'] = all_users
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
                            'film': film.title,
                            'voter': voter,
                        })
                elif voter not in participants:
                    if vote.choice == Vote.OMG:
                        warnings.append({
                            'type': Vote.OMG,
                            'film': film.title,
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
        for film in Film.objects.filter(seen=False):
            voters_info, warnings, points, veto = process(film, participants)
            films_results.append({
                'id': film.id,
                'title': film.title,
                'positive_voters': voters_info[0],
                'negative_voters': voters_info[1],
                'no_voters': voters_info[2],
                'points': points,
                'veto': veto,
                })
            films_warnings.extend(warnings)
        context['films_results'] = films_results
        context['warnings'] = films_warnings
        context['participants'] = participants
        return context
