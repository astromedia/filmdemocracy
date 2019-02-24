import requests
import random

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from filmdemocracy.democracy import forms
from filmdemocracy.democracy.models import Club, ClubMemberInfo
from filmdemocracy.democracy.models import ShoutboxPost, Meeting
from filmdemocracy.democracy.models import FilmDb, Film, Vote, FilmComment
from filmdemocracy.registration.models import User
from filmdemocracy.settings import OMDB_API_KEY


def user_is_club_member_check(request, club_id):
    user = request.user
    club = get_object_or_404(Club, pk=club_id)
    club_members = club.members.filter(is_active=True)
    return user in club_members


def user_is_club_admin_check(request, club_id):
    user = request.user
    club = get_object_or_404(Club, pk=club_id)
    club_members = club.members.filter(is_active=True)
    club_admins = club.admin_members.filter(is_active=True)
    return user in club_members and user in club_admins


def user_is_organizer_check(request, club_id, meeting_id):
    user = request.user
    club = get_object_or_404(Club, pk=club_id)
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    club_members = club.members.filter(is_active=True)
    return user in club_members and user == meeting.organizer


def add_club_context(request, context, club_id):
    club = get_object_or_404(Club, pk=club_id)
    context['club'] = club
    context['club_members'] = club.members.filter(is_active=True)
    context['club_admins'] = club.admin_members.filter(is_active=True)
    context['user'] = request.user
    return context


@method_decorator(login_required, name='dispatch')
class CreateClubView(generic.FormView):
    form_class = forms.EditClubForm

    def get_success_url(self):
        # TODO: redirect to club view
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
        user = self.request.user
        new_club = Club.objects.create(
            id=self.random_id_generator(),
            name=form.cleaned_data['name'],
            short_description=form.cleaned_data['short_description'],
            logo=form.cleaned_data['logo'],
        )
        new_club.admin_members.add(user)
        new_club.members.add(user)
        new_club.save()
        club_member_info = ClubMemberInfo.objects.create(
            club=new_club,
            member=user,
        )
        club_member_info.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class ClubDetailView(UserPassesTestMixin, generic.DetailView):
    model = Club
    pk_url_kwarg = 'club_id'

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['club_id']
        context = add_club_context(self.request, context, club_id)
        club_meetings = Meeting.objects.filter(
            club_id=club_id,
            date__gte=timezone.now().date()
        )
        if club_meetings:
            context['next_meetings'] = club_meetings.order_by('date')[0:3]
        last_comments = FilmComment.objects.filter(club_id=club_id, deleted=False)
        if last_comments:
            context['last_comments'] = last_comments.order_by('-date')[0:5]
        club_films = Film.objects.filter(club_id=club_id)
        if club_films:
            films_last_pub = club_films.order_by('-pub_date')
            groups_last_pub = [films_last_pub[i:i+4] for i in [0, 4, 8, 12]]
            context['groups_last_pub'] = groups_last_pub
            last_seen = club_films.filter(seen=True)
            context['films_last_seen'] = last_seen.order_by('-seen_date')[0:5]
        return context


@method_decorator(login_required, name='dispatch')
class ClubMemberDetailView(UserPassesTestMixin, generic.DetailView):
    model = User
    pk_url_kwarg = 'user_id'

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['club_id']
        context = add_club_context(self.request, context, club_id)
        club = context['club']
        member = get_object_or_404(User, pk=self.kwargs['user_id'])
        context['member'] = member
        club_member_info = get_object_or_404(
            ClubMemberInfo,
            club=club,
            member=member,
        )
        context['club_member_info'] = club_member_info
        all_votes = member.vote_set.filter(club_id=club.id)
        context['num_of_votes'] = all_votes.count()
        club_films = Film.objects.filter(club_id=club.id)
        club_films_seen = club_films.filter(seen=False)
        votes = [vote for vote in all_votes if vote.film in club_films_seen]
        context['member_votes'] = votes
        member_seen_films = member.seen_by.filter(club_id=club.id)
        context['member_seen_films'] = member_seen_films
        context['num_of_films_seen'] = member_seen_films.count()
        proposed = club_films.filter(proposed_by=member)
        context['num_of_films_proposed'] = proposed.count()
        return context


@method_decorator(login_required, name='dispatch')
class EditClubInfoView(UserPassesTestMixin, generic.UpdateView):
    model = Club
    pk_url_kwarg = 'club_id'
    form_class = forms.EditClubForm

    def test_func(self):
        return user_is_club_admin_check(self.request, self.kwargs['club_id'])

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'club_id': self.kwargs['club_id']}
        )


@method_decorator(login_required, name='dispatch')
class EditClubPanelView(UserPassesTestMixin, generic.UpdateView):
    model = Club
    pk_url_kwarg = 'club_id'
    fields = ['panel']

    def test_func(self):
        return user_is_club_admin_check(self.request, self.kwargs['club_id'])

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'club_id': self.kwargs['club_id']}
        )


@login_required
def leave_club(request, club_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    context = {}
    context = add_club_context(request, context, club_id)
    club = context['club']
    club_members = context['club_members']
    club_admins = context['club_admins']
    user = request.user
    if user in club_admins:
        if len(club_members) > 1 and len(club_admins) == 1:
            context['warning_message'] = \
                _("You must promote other club member "
                  "to admin before leaving the club.")
            return render(request, 'democracy/club_detail.html', context)
        else:
            club.admin_members.remove(user)
    club.members.remove(user)
    club.save()
    club_member_info = get_object_or_404(
        ClubMemberInfo,
        club=club,
        member=user,
    )
    club_member_info.delete()
    # TODO: Message: 'You have successfully left the club.'
    if len(club_members) == 1:
        club.delete()
    return HttpResponseRedirect(reverse('home'))


@login_required
def self_demote(request, club_id):
    if not user_is_club_admin_check(request, club_id):
        return HttpResponseForbidden()
    context = {}
    context = add_club_context(request, context, club_id)
    club = context['club']
    club_admins = context['club_admins']
    user = request.user
    if user in club_admins:
        if len(club_admins) == 1:
            context['warning_message'] = \
                _("You must promote other club member "
                  "to admin before demoting yourself.")
            return render(request, 'democracy/club_detail.html', context)
        else:
            club.admin_members.remove(user)
    club.save()
    # TODO: Message: 'You have successfully demoted yourself.'
    return HttpResponseRedirect(reverse_lazy(
        'democracy:club_detail',
        kwargs={'club_id': club.id}
    ))


@method_decorator(login_required, name='dispatch')
class KickMembersView(UserPassesTestMixin, generic.FormView):
    form_class = forms.KickMembersForm

    def test_func(self):
        return user_is_club_admin_check(self.request, self.kwargs['club_id'])

    def get_form_kwargs(self):
        kwargs = super(KickMembersView, self).get_form_kwargs()
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_members = club.members.filter(is_active=True)
        kickable_members = club_members.exclude(pk=self.request.user.id)
        kwargs.update({'kickable_members': kickable_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'club_id': self.kwargs['club_id']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['club_id']
        context = add_club_context(self.request, context, club_id)
        return context

    def form_valid(self, form):
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_admins = club.admin_members.all()
        kicked_members = form.cleaned_data['members']
        for member in kicked_members:
            if member in club_admins:
                club.admin_members.remove(member)
            club.members.remove(member)
            club_member_info = get_object_or_404(
                ClubMemberInfo,
                club=club,
                member=member,
            )
            club_member_info.delete()
        club.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class PromoteMembersView(UserPassesTestMixin, generic.FormView):
    form_class = forms.PromoteMembersForm

    def test_func(self):
        return user_is_club_admin_check(self.request, self.kwargs['club_id'])

    def get_form_kwargs(self):
        kwargs = super(PromoteMembersView, self).get_form_kwargs()
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_members = club.members.filter(is_active=True)
        promotable_members = club_members.exclude(pk=self.request.user.id)
        kwargs.update({'promotable_members': promotable_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'club_id': self.kwargs['club_id']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['club_id']
        context = add_club_context(self.request, context, club_id)
        return context

    def form_valid(self, form):
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        promoted_members = form.cleaned_data['members']
        for member in promoted_members:
            club.admin_members.add(member)
        club.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CandidateFilmsView(UserPassesTestMixin, generic.TemplateView):
    # TODO: change to ListView?

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        club_films = Film.objects.filter(club_id=club.id)
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
class SeenFilmsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        seen_films = Film.objects.filter(club_id=club.id, seen=True)
        context['seen_films'] = seen_films
        return context


@method_decorator(login_required, name='dispatch')
class FilmSeenSelectionView(UserPassesTestMixin, generic.TemplateView):
    # TODO: change to ListView?

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        club_films = Film.objects.filter(club_id=club.id)
        context['candidate_films'] = club_films.filter(seen=False)
        return context


@method_decorator(login_required, name='dispatch')
class AddNewFilmView(UserPassesTestMixin, generic.FormView):
    form_class = forms.FilmAddNewForm

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

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

    @staticmethod
    def random_id_generator(club_id):
        """
        Random id generator, picks an integer in the [1, 99999] range
        and checks if it is already used (i.e., not found in the DB).
        return: new_id: new id number not existing in the database
        """
        club_films = Film.objects.filter(club_id=club_id)
        films_ids = [fid[-5:] for fid in club_films.values_list('id', flat=True)]
        free_ids = [i for i in range(1, 99999) if i not in films_ids]
        return f'{random.choice(free_ids):05d}'

    def form_valid(self, form):
        imdb_id = form.cleaned_data['imdb_url']
        filmdb, created = FilmDb.objects.get_or_create(imdb_id=imdb_id)
        if created or (not created and not filmdb.title):
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
            filmdb.duration = omdb_data['Runtime']
            filmdb.language = omdb_data['Language']
            filmdb.rated = omdb_data['Rated']
            filmdb.country = omdb_data['Country']
            filmdb.plot = omdb_data['Plot']
            filmdb.save()
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        new_film_id = self.random_id_generator(club.id)
        Film.objects.create(
            id=f'{club.id}{new_film_id}',
            imdb_id=imdb_id,
            proposed_by=self.request.user,
            club=club,
            filmdb=filmdb,
        )
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class FilmDetailView(UserPassesTestMixin, generic.TemplateView):
    # TODO: Change to DetailView?
    model = Film

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = add_club_context(self.request, context, self.kwargs['club_id'])
        film = get_object_or_404(Film, pk=self.kwargs['film_id'])
        context['film'] = film
        if 'min' in film.filmdb.duration:
            context['film_runtime'] = film.filmdb.duration.replace('min', ' min')
        else:
            context['film_runtime'] = film.filmdb.duration
        film_comments = FilmComment.objects.filter(
            club=self.kwargs['club_id'],
            film=self.kwargs['film_id']
        )
        context['film_comments'] = film_comments.order_by('date')

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


@login_required
def vote_film(request, club_id, film_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
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


@login_required
def comment_film(request, club_id, film_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    film_comment = FilmComment.objects.create(
        user=request.user,
        film=film,
        club=club,
        text=request.POST['text']
    )
    film_comment.save()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'club_id': club_id,
                'film_id': film_id}
    ))


@login_required
def delete_film_comment(request, club_id, film_id, comment_id):
    film_comment = get_object_or_404(FilmComment, id=comment_id)
    if request.user != film_comment.user:
        if not user_is_club_admin_check(request, club_id):
            return HttpResponseForbidden()
    film_comment.deleted = True
    film_comment.save()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'club_id': club_id,
                'film_id': film_id}
    ))


@method_decorator(login_required, name='dispatch')
class FilmAddFilmAffView(UserPassesTestMixin, generic.FormView):
    form_class = forms.FilmAddFilmAffForm

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_success_url(self):
        return reverse_lazy(
            'democracy:film_detail',
            kwargs={'club_id': self.kwargs['club_id'],
                    'film_id': self.kwargs['film_id']}
        )

    def form_valid(self, form):
        film = get_object_or_404(Film, id=self.kwargs['film_id'])
        filmdb = get_object_or_404(FilmDb, imdb_id=film.filmdb.imdb_id)
        filmdb.faff_id = form.cleaned_data['faff_url']
        filmdb.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['film'] = get_object_or_404(Film, pk=self.kwargs['film_id'])
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context


@method_decorator(login_required, name='dispatch')
class FilmSeenView(UserPassesTestMixin, generic.FormView):
    form_class = forms.FilmSeenForm

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

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


@login_required
def delete_film(request, club_id, film_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    film.delete()
    return HttpResponseRedirect(reverse(
        'democracy:candidate_films',
        kwargs={'club_id': club_id}
    ))


@method_decorator(login_required, name='dispatch')
class ParticipantsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        context['club_members'] = club.members.filter(is_active=True)
        return context


@method_decorator(login_required, name='dispatch')
class VoteResultsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        def process_film(film, participants, **options):
            warnings = []
            film_all_votes = film.vote_set.all()
            film_voters = [vote.user for vote in film_all_votes]
            abstentionists = []
            positive_voters = []
            negative_voters = []
            for participant in participants:
                if participant not in film_voters:
                    abstentionists.append(participant)
            film_votes = []
            for vote in film_all_votes:
                if vote.user in participants:
                    film_votes.append(vote.choice)
                    if vote.vote_karma is 'positive':
                        positive_voters.append(vote.user)
                    elif vote.vote_karma is 'negative':
                        negative_voters.append(vote.user)
                    else:
                        pass
                    if vote.choice == Vote.VETO:
                        warnings.append({
                            'type': Vote.VETO,
                            'film': film.filmdb.title,
                            'voter': vote.user.username,
                        })
                elif vote.user not in participants:
                    if vote.choice == Vote.OMG:
                        warnings.append({
                            'type': Vote.OMG,
                            'film': film.filmdb.title,
                            'voter': vote.user.username,
                        })
                    if vote.user == film.proposed_by:
                        warnings.append({
                            'type': 'proposer missing',
                            'film': film.filmdb.title,
                            'voter': vote.user.username,
                        })
            voters_meta = (positive_voters, negative_voters, abstentionists)

            # TODO: use aggregations to do this count
            n_veto = film_votes.count(Vote.VETO)
            n_seenno = film_votes.count(Vote.SEENNO)
            n_no = film_votes.count(Vote.NO)
            n_meh = film_votes.count(Vote.MEH)
            n_seenok = film_votes.count(Vote.SEENOK)
            n_yes = film_votes.count(Vote.YES)
            n_omg = film_votes.count(Vote.OMG)
            if n_veto >= 1:
                return voters_meta, warnings, -1000, True
            else:
                points = (
                        - 50 * n_seenno
                        - 25 * n_no
                        + 0 * n_meh
                        + 5 * n_seenok
                        + 10 * n_yes
                        + 20 * n_omg
                )
                return voters_meta, warnings, points, False

        films_results = []
        participants = [User.objects.filter(id=id)[0]
                        for id in self.request.GET.getlist('participants')]
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_films = Film.objects.filter(club_id=club.id, seen=False)
        for film in club_films:
            voters_meta, warnings, points, veto = process_film(film, participants)
            films_results.append({
                'id': film.id,
                'title': film.filmdb.title,
                'positive_voters': voters_meta[0],
                'negative_voters': voters_meta[1],
                'abstentionists': voters_meta[2],
                'points': points,
                'veto': veto,
                'warnings': warnings,
            })
        context['club'] = club
        context['films_results'] = films_results
        context['participants'] = participants
        return context


@method_decorator(login_required, name='dispatch')
class InviteNewMemberView(UserPassesTestMixin, generic.FormView):
    # TODO: Multiple invitations in one form
    form_class = forms.InviteNewMemberForm
    subject_template_name = 'democracy/invite_new_member_subject.txt'
    email_template_name = 'democracy/invite_new_member_email.html'
    html_email_template_name = 'democracy/invite_new_member_email_html.html'
    extra_email_context = None
    from_email = 'filmdemocracyweb@gmail.com'

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(InviteNewMemberView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        return kwargs

    def form_valid(self, form):
        email_opts = {
            'subject_template_name': self.subject_template_name,
            'email_template_name': self.email_template_name,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
            'use_https': self.request.is_secure(),
            'from_email': self.from_email,
            'request': self.request,
        }
        form.save(**email_opts)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'democracy:invite_new_member_done',
            kwargs={'club_id': self.kwargs['club_id']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context


@method_decorator(login_required, name='dispatch')
class InviteNewMemberDoneView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context


@method_decorator(login_required, name='dispatch')
class InviteNewMemberConfirmView(generic.FormView):
    form_class = forms.InviteNewMemberConfirmForm

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        assert 'uinviteridb64' in kwargs
        assert 'uemailb64' in kwargs
        assert 'uclubidb64' in kwargs
        self.validlink = False
        user = self.request.user
        inviter = self.get_object(User, self.kwargs['uinviteridb64'])
        email = urlsafe_base64_decode(self.kwargs['uemailb64']).decode()
        club = self.get_object(Club, self.kwargs['uclubidb64'])

        if club is not None and user.email == email:
            club_members = club.members.filter(is_active=True)
            if inviter in club_members and user not in club_members:
                self.validlink = True
                return super().dispatch(*args, **kwargs)
        # Display the "invitation link not valid" error page.
        return self.render_to_response(self.get_context_data())

    def get_object(self, object_model, uobjectidb64):
        try:
            uobjectid = urlsafe_base64_decode(uobjectidb64).decode()
            object = object_model.objects.get(pk=uobjectid)
        except (TypeError, ValueError, OverflowError,
                object_model.DoesNotExist, ValidationError):
            object = None
        return object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.validlink:
            club = self.get_object(Club, self.kwargs['uclubidb64'])
            context['validlink'] = True
            context['club'] = club
        else:
            context.update({
                'form': None,
                'validlink': False,
            })
        return context

    def form_valid(self, form):
        user = self.request.user
        club = self.get_object(Club, self.kwargs['uclubidb64'])
        club_members = club.members.filter(is_active=True)
        if user not in club_members:
            club.members.add(self.request.user)
            club.save()
            club_member_info = ClubMemberInfo.objects.create(
                club=club,
                member=user,
            )
            club_member_info.save()
        return super().form_valid(form)

    def get_success_url(self):
        club = self.get_object(Club, self.kwargs['uclubidb64'])
        return reverse_lazy(
            'democracy:invite_new_member_complete',
            kwargs={'club_id': club.id}
        )


@method_decorator(login_required, name='dispatch')
class InviteNewMemberCompleteView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context


@method_decorator(login_required, name='dispatch')
class MeetingsNewView(UserPassesTestMixin, generic.FormView):
    form_class = forms.MeetingsForm
    subject_template_name = 'democracy/new_meeting_subject.txt'
    email_template_name = 'democracy/new_meeting_email.html'
    html_email_template_name = 'democracy/new_meeting_email_html.html'
    extra_email_context = None
    from_email = 'filmdemocracyweb@gmail.com'

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_form_kwargs(self):
        kwargs = super(MeetingsNewView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'club_id': self.kwargs['club_id']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context

    @staticmethod
    def random_id_generator(club_id):
        club_meetings = Meeting.objects.filter(club_id=club_id)
        meetings_ids = [mid[-4:] for mid in club_meetings.values_list('id', flat=True)]
        free_ids = [i for i in range(1, 9999) if i not in meetings_ids]
        return f'{random.choice(free_ids):04d}'

    def form_valid(self, form):
        user = self.request.user
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        new_meeting = Meeting.objects.create(
            id=f'{int(club.id):05d}{self.random_id_generator(club.id)}',
            club=club,
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description'],
            organizer=user,
            place=form.cleaned_data['place'],
            date=form.cleaned_data['date'],
            time_start=form.cleaned_data['time_start'],
            time_end=form.cleaned_data['time_end'],
        )
        new_meeting.save()
        email_opts = {
            'subject_template_name': self.subject_template_name,
            'email_template_name': self.email_template_name,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
            'use_https': self.request.is_secure(),
            'from_email': self.from_email,
            'request': self.request,
        }
        form.save(**email_opts)
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class MeetingsEditView(UserPassesTestMixin, generic.UpdateView):
    pk_url_kwarg = 'meeting_id'
    model = Meeting
    form_class = forms.MeetingsForm

    def test_func(self):
        return user_is_organizer_check(
            self.request,
            self.kwargs['club_id'],
            self.kwargs['meeting_id']
        )

    def get_success_url(self):
        return reverse_lazy(
            'democracy:club_detail',
            kwargs={'club_id': self.kwargs['club_id']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context


@login_required
def meeting_assistance(request, club_id, meeting_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    user = request.user
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    if 'yes' in request.POST:
        if user in meeting.members_yes.all():
            meeting.members_yes.remove(user)
        else:
            if user in meeting.members_maybe.all():
                meeting.members_maybe.remove(user)
            meeting.members_yes.add(user)
    elif 'maybe' in request.POST:
        if user in meeting.members_maybe.all():
            meeting.members_maybe.remove(user)
        else:
            if user in meeting.members_yes.all():
                meeting.members_yes.remove(user)
            meeting.members_maybe.add(user)
    meeting.save()
    return HttpResponseRedirect(reverse(
        'democracy:club_detail',
        kwargs={'club_id': club_id}
    ))


@login_required
def delete_meeting(request, club_id, meeting_id):
    organizer_check = user_is_organizer_check(request, club_id, meeting_id)
    admin_check = user_is_club_admin_check(request, club_id)
    if not organizer_check and not admin_check:
        return HttpResponseForbidden()
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    meeting.delete()
    return HttpResponseRedirect(reverse(
        'democracy:club_detail',
        kwargs={'club_id': club_id}
    ))


@method_decorator(login_required, name='dispatch')
class MeetingsListView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = add_club_context(self.request, context, self.kwargs['club_id'])
        club_meetings = Meeting.objects.filter(
            club_id=self.kwargs['club_id'],
            date__gte=timezone.now().date()
        )
        context['club_meetings'] = club_meetings.order_by('date')
        return context


@method_decorator(login_required, name='dispatch')
class ShoutboxView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = add_club_context(self.request, context, self.kwargs['club_id'])
        posts = ShoutboxPost.objects.filter(
            club=self.kwargs['club_id'],
        )
        context['posts'] = posts.order_by('-date')[:1000]
        return context


@login_required
def post_in_shoutbox(request, club_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    club = get_object_or_404(Club, pk=club_id)
    post = ShoutboxPost.objects.create(
        user=request.user,
        club=club,
        text=request.POST['text']
    )
    post.save()
    return HttpResponseRedirect(reverse(
        'democracy:shoutbox',
        kwargs={'club_id': club_id}
    ))


@login_required
def delete_shoutbox_post(request, club_id, post_id):
    post = get_object_or_404(ShoutboxPost, id=post_id)
    if request.user != post.user:
        if not user_is_club_admin_check(request, club_id):
            return HttpResponseForbidden()
    post.deleted = True
    post.save()
    return HttpResponseRedirect(reverse(
        'democracy:shoutbox',
        kwargs={'club_id': club_id}
    ))
