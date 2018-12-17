from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User

from filmdemocracy.democracy.forms import FilmAddNewForm
from filmdemocracy.democracy.models import Film, Vote


@method_decorator(login_required, name='dispatch')
class FilmListView(generic.TemplateView):
    template_name = 'democracy/film_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_of_films'] = Film.objects.all().order_by('title')
        context['last_proposed_films'] = Film.objects.all().order_by('-pub_date')
        context['last_seen_films'] = Film.objects.all().order_by('-seen_date')
        return context


@method_decorator(login_required, name='dispatch')
class FilmAddNewView(generic.FormView):
    form_class = FilmAddNewForm
    template_name = 'democracy/film_add_new.html'

    @staticmethod
    def imdb_id_from_url(url):
        if 'imdb' in url:
            url_list = url.split('/')
            title_position = url_list.index('title')
            return url_list[title_position + 1]
        else:
            raise Exception('Unknown url movie database.')

    def get_success_url(self):
        return reverse('democracy:film_list')

    def form_valid(self, form):
        imdb_url = self.imdb_id_from_url(form.cleaned_data['url'])
        Film.objects.create(
            title=form.cleaned_data['title'],
            imdb_id=imdb_url,
            proposed_by=self.request.user
        )
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class FilmDetailView(generic.DetailView):
    model = Film
    template_name = 'democracy/film_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        choice_dict = {choice[0]: choice[1] for choice in Vote.vote_choices}
        context['vote_choices'] = choice_dict
        return context


def vote_film(request, film_id):
    film = get_object_or_404(Film, pk=film_id)
    user_vote, _ = Vote.objects.get_or_create(
        user=request.user,
        film=film,
    )
    try:
        user_vote.choice = request.POST['choice']
    except KeyError:
        choice_dict = {choice[0]: choice[1] for choice in Vote.vote_choices}
        return render(
            request,
            'democracy/film_detail.html', {
                'film': film,
                'error_message': "Tienes que elegir tu voto.",
                'vote_choices': choice_dict
            }
        )
    else:
        user_vote.save()
        return HttpResponseRedirect(reverse('democracy:film_list'))


@method_decorator(login_required, name='dispatch')
class FilmDeleteView(generic.DeleteView):
    model = Film
    success_url = reverse_lazy('democracy:film_list')
    template_name = 'democracy/film_delete_confirm.html'


@method_decorator(login_required, name='dispatch')
class FilmSeenView(generic.UpdateView):
    model = Film
    fields = ['seen_date']
    success_url = reverse_lazy('democracy:film_list')
    template_name = 'democracy/film_seen.html'

    def form_valid(self, form):
        form.instance.seen = True
        return super().form_valid(form)


def unsee_film(request, film_id):
    film = get_object_or_404(Film, pk=film_id)
    film.seen = False
    film.seen_date = None
    film.save()
    return HttpResponseRedirect(reverse('democracy:film_list'))


@method_decorator(login_required, name='dispatch')
class ParticipantsView(generic.TemplateView):
    template_name = 'democracy/participants.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_users = User.objects.filter(is_superuser=False)
        context['all_users'] = all_users
        return context


@method_decorator(login_required, name='dispatch')
class VoteResultsView(generic.TemplateView):
    template_name = 'democracy/vote_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        def process(film, participants):
            warnings = []
            film_votes = []
            film_voters = []
            film_all_votes = film.vote_set.all()
            for vote in film_all_votes:
                voter = vote.user.username
                film_voters.append(voter)
                if voter in participants:
                    film_votes.append(vote.choice)
                    if vote.choice == Vote.VETO:
                        warnings.append(f'{voter} vetó {film.title}.')
                elif voter not in participants:
                    if vote.choice == Vote.OMG:
                        warnings.append(f'No veáis {film.title} sin {voter}.')
            for participant in participants:
                if participant not in film_voters:
                    warnings.append(f'{participant} todavía '
                                    f'no ha votado {film.title}.')
            # TODO: use aggregations to do this count
            n_veto = film_votes.count(Vote.VETO)
            n_seenno = film_votes.count(Vote.SEENNO)
            n_no = film_votes.count(Vote.NO)
            n_meh = film_votes.count(Vote.MEH)
            n_seenok = film_votes.count(Vote.SEENOK)
            n_yes = film_votes.count(Vote.YES)
            n_omg = film_votes.count(Vote.OMG)
            if n_veto >= 1:
                return warnings, -1000, True
            else:
                film_points = (
                    - 50 * n_seenno
                    - 25 * n_no
                    + 0 * n_meh
                    + 5 * n_seenok
                    + 10 * n_yes
                    + 20 * n_omg
                )
                return warnings, film_points, False

        films_results = []
        films_warnings = []
        participants = self.request.GET.getlist('participants')
        for film in Film.objects.all():
            warnings, film_points, film_veto = process(film, participants)
            films_results.append({'title': film.title,
                                 'points': film_points,
                                 'veto': film_veto,
                                 })
            films_warnings.extend(warnings)
        context['films_results'] = films_results
        context['warnings'] = films_warnings
        context['participants'] = participants
        return context
