import requests
import random

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic

from filmdemocracy.democracy import forms
from filmdemocracy.democracy.models import Club, FilmDb, Film, Vote
from filmdemocracy.registration.models import User
from filmdemocracy.settings import OMDB_API_KEY


def get_club_context(view_request, club_id, context):
    club = get_object_or_404(Club, pk=club_id)
    context['club'] = club
    context['club_members'] = club.members.filter(is_active=True)
    context['club_admins'] = club.admin_members.all()
    context['user'] = view_request.user
    return context


@method_decorator(login_required, name='dispatch')
class CreateClubView(generic.FormView):
    form_class = forms.CreateClubForm

    def get_success_url(self):
        return reverse('home')

    @staticmethod
    def random_id_generator():
        """
        Random id generator, that picks an integer in the [1, 99999] range
        among the free ones (i.e., not found in the DB).
        return: new_id: new id number not existing in the database
        """
        if len(Club.objects.all()) == 99999:
            raise Exception('All possible id numbers are picked!')
        else:
            club_ids = Club.objects.values_list('id', flat=True)
            free_ids = [i for i in range(1, 99999) if i not in club_ids]
            return f'{random.choice(free_ids):05d}'

    def form_valid(self, form):
        default_club_panel = _(
            "## A sample club panel written in markdown"
            "\r\n"
            "\r\n---"
            "\r\n"
            "\r\n#### Point 1: Here is some text. "
            "\r\nHello world, I'm a cinema club... "
            "\r\n"
            "\r\n#### Point 2: And here is a list to consider: "
            "\r\n1. Item #1"
            "\r\n2. Item #2"
            "\r\n3. Item #3"
            "\r\n"
            "\r\n#### Point 3: And here is an unordered list to consider:"
            "\r\n- Item 1"
            "\r\n- Item 2"
            "\r\n- Item 3"
        )
        new_club = Club.objects.create(
            id=self.random_id_generator(),
            name=form.cleaned_data['name'],
            short_description=form.cleaned_data['short_description'],
            panel=default_club_panel,
            logo=form.cleaned_data['logo'],
        )
        new_club.admin_users.add(self.request.user)
        new_club.users.add(self.request.user)
        new_club.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class ClubDetailView(generic.DetailView):
    model = Club

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['pk']
        context = get_club_context(self.request, club_id, context)
        club_films = Film.objects.all().filter(club_id=club_id)
        context['films_last_pub'] = club_films.order_by('-pub_date')
        last_seen = club_films.filter(seen=True)
        context['films_last_seen'] = last_seen.order_by('-seen_date')
        return context


@method_decorator(login_required, name='dispatch')
class ClubMemberDetailView(generic.DetailView):
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['club_id']
        context = get_club_context(self.request, club_id, context)
        club = context['club']
        member = get_object_or_404(User, pk=self.kwargs['pk'])
        context['member'] = member
        all_votes = member.vote_set.filter(club_id=club.id)
        context['num_of_votes'] = all_votes.count()
        club_films = Film.objects.all().filter(club_id=club.id, seen=False)
        votes = [vote for vote in all_votes if vote.film in club_films]
        context['member_votes'] = votes
        member_seen_films = member.seen_by.filter(club_id=club.id)
        context['member_seen_films'] = member_seen_films
        context['num_of_films_seen'] = member_seen_films.count()
        return context


@method_decorator(login_required, name='dispatch')
class EditClubInfoView(generic.UpdateView):
    model = Club
    fields = ['name', 'logo', 'short_description']

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'pk': self.kwargs['pk']}
        )


@method_decorator(login_required, name='dispatch')
class EditClubPanelView(generic.UpdateView):
    model = Club
    fields = ['panel']

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'pk': self.kwargs['pk']}
        )


def leave_club(request, club_id):
    context = {}
    context = get_club_context(request, club_id, context)
    club = context['club']
    club_admins = context['club_admins']
    user = request.user
    if user in club_admins:
        if len(club_admins) == 1:
            context['warning_message'] = \
                _("You must promote other club member "
                  "to admin before leaving the club.")
            return render(request, 'democracy/club_detail.html', context)
        else:
            club.admin_members.remove(user)
    club.members.remove(user)
    club.save()
    # TODO: Message: 'You have successfully left the club.'
    return HttpResponseRedirect(reverse('home'))


def self_demote(request, club_id):
    context = {}
    context = get_club_context(request, club_id, context)
    club = context['club']
    club_admins = context['club_admins']
    user = request.user
    if user in club_admins:
        if len(club_admins) == 1:
            context['warning_message'] =\
                _("You must promote other club member "
                  "to admin before demoting yourself.")
            return render(request, 'democracy/club_detail.html', context)
        else:
            club.admin_members.remove(user)
    club.save()
    # TODO: Message: 'You have successfully demoted yourself.'
    return HttpResponseRedirect(reverse_lazy(
            'democracy:club_detail',
            kwargs={'pk': club_id}
        ))


@method_decorator(login_required, name='dispatch')
class KickMembersView(generic.FormView):
    form_class = forms.KickMembersForm

    def get_form_kwargs(self):
        kwargs = super(KickMembersView, self).get_form_kwargs()
        club = get_object_or_404(Club, pk=self.kwargs['pk'])
        club_members = club.members.filter(is_active=True)
        kickable_members = club_members.exclude(pk=self.request.user.id)
        kwargs.update({'kickable_members': kickable_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'pk': self.kwargs['pk']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_club_context(self.request, self.kwargs['pk'], context)
        return context

    def form_valid(self, form):
        club = get_object_or_404(Club, pk=self.kwargs['pk'])
        club_admins = club.admin_members.all()
        kicked_members = form.cleaned_data['members']
        for member in kicked_members:
            if member in club_admins:
                club.admin_members.remove(member)
            club.members.remove(member)
        club.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class PromoteMembersView(generic.FormView):
    form_class = forms.PromoteMembersForm

    def get_form_kwargs(self):
        kwargs = super(PromoteMembersView, self).get_form_kwargs()
        club = get_object_or_404(Club, pk=self.kwargs['pk'])
        club_members = club.members.filter(is_active=True)
        promotable_members = club_members.exclude(pk=self.request.user.id)
        kwargs.update({'promotable_members': promotable_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'pk': self.kwargs['pk']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_club_context(self.request, self.kwargs['pk'], context)
        return context

    def form_valid(self, form):
        club = get_object_or_404(Club, pk=self.kwargs['pk'])
        promoted_members = form.cleaned_data['members']
        for member in promoted_members:
            club.admin_members.add(member)
        club.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CandidateFilmsView(generic.TemplateView):
    # TODO: change to ListView?

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
    # TODO: Change to DetailView?
    model = Film

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
    return HttpResponseRedirect(reverse(
        'democracy:candidate_films',
        kwargs={'club_id': club_id}
    ))


@method_decorator(login_required, name='dispatch')
class FilmAddFilmAffView(generic.FormView):
    form_class = forms.FilmAddFilmAffForm

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
        kwargs.update({'club_members': club.members.filter(is_active=True)})
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
        context['club_members'] = club.members.filter(is_active=True)
        return context


def unsee_film(request, club_id, film_id):
    film = get_object_or_404(Film, pk=film_id)
    film.seen = False
    film.seen_date = None
    film.save()
    return HttpResponseRedirect(reverse_lazy(
        'democracy:film_detail',
        kwargs={'club_id': club_id, 'film_id': film_id}
    ))


def delete_film(request, club_id, film_id):
    film = get_object_or_404(Film, pk=film_id)
    film.delete()
    return HttpResponseRedirect(reverse(
        'democracy:candidate_films',
        kwargs={'club_id': club_id}
    ))


@method_decorator(login_required, name='dispatch')
class ParticipantsView(generic.TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        context['club_members'] = club.members.filter(is_active=True)
        return context


@method_decorator(login_required, name='dispatch')
class VoteResultsView(generic.TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        def process(in_film, in_participants):
            out_warnings = []
            film_all_votes = in_film.vote_set.all()
            film_voters = [vote.user.username for vote in film_all_votes]
            no_voters = []
            for participant in in_participants:
                if participant not in film_voters:
                    no_voters.append(participant)
            film_votes = []
            positive_voters = []
            negative_voters = []
            for vote in film_all_votes:
                voter = vote.user.username
                if voter in in_participants:
                    film_votes.append(vote.choice)
                    if vote.vote_karma is 'positive':
                        positive_voters.append(voter)
                    elif vote.vote_karma is 'negative':
                        negative_voters.append(voter)
                    if vote.choice == Vote.VETO:
                        out_warnings.append({
                            'type': Vote.VETO,
                            'film': film.filmdb.title,
                            'voter': voter,
                        })
                elif voter not in in_participants:
                    if vote.choice == Vote.OMG:
                        out_warnings.append({
                            'type': Vote.OMG,
                            'film': film.filmdb.title,
                            'voter': voter,
                        })
            out_voters_info = (positive_voters, negative_voters, no_voters)

            # TODO: use aggregations to do this count
            n_veto = film_votes.count(Vote.VETO)
            n_seenno = film_votes.count(Vote.SEENNO)
            n_no = film_votes.count(Vote.NO)
            n_meh = film_votes.count(Vote.MEH)
            n_seenok = film_votes.count(Vote.SEENOK)
            n_yes = film_votes.count(Vote.YES)
            n_omg = film_votes.count(Vote.OMG)
            if n_veto >= 1:
                return out_voters_info, out_warnings, -1000, True
            else:
                out_points = (
                        - 50 * n_seenno
                        - 25 * n_no
                        + 0 * n_meh
                        + 5 * n_seenok
                        + 10 * n_yes
                        + 20 * n_omg
                )
                return out_voters_info, out_warnings, out_points, False

        films_results = []
        films_warnings = []
        participants = self.request.GET.getlist('participants')
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_films = Film.objects.all().filter(club_id=club.id, seen=False)
        for film in club_films:
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
