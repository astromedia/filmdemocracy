import random
import requests

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404
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
from filmdemocracy.democracy.models import ChatClubPost, ChatUsersPost, ChatUsersInfo, ChatClubInfo, Meeting
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


def users_know_each_other_check(request, chatuser_id):
    user = request.user
    chat_user = get_object_or_404(User, pk=chatuser_id)
    common_clubs = user.club_set.all() & chat_user.club_set.all()
    chat_opened = ChatUsersInfo.objects.filter(user=user, user_known=chat_user)
    if common_clubs.exists() or chat_opened.exists():
        return True
    else:
        return False


def add_club_context(request, context, club_id):
    club = get_object_or_404(Club, pk=club_id)
    context['club'] = club
    context['club_members'] = club.members.filter(is_active=True)
    context['club_admins'] = club.admin_members.filter(is_active=True)
    context['user'] = request.user
    return context


def update_filmdb_omdb_info(filmdb, imdb_id):
    omdb_api_url = f'http://www.omdbapi.com/?i=tt{imdb_id}&plot=full&apikey={OMDB_API_KEY}'
    response = requests.get(omdb_api_url)
    omdb_data = response.json()
    filmdb.title = omdb_data['Title']
    filmdb.year = omdb_data['Year']
    filmdb.director = omdb_data['Director']
    filmdb.writer = omdb_data['Writer']
    filmdb.actors = omdb_data['Actors']
    filmdb.poster_url = omdb_data['Poster']
    if ' min' in omdb_data['Runtime']:
        filmdb.duration = omdb_data['Runtime'].replace(' min', '')
    elif 'min' in omdb_data['Runtime']:
        filmdb.duration = omdb_data['Runtime'].replace('min', '')
    else:
        filmdb.duration = omdb_data['Runtime']
    filmdb.language = omdb_data['Language']
    filmdb.rated = omdb_data['Rated']
    filmdb.country = omdb_data['Country']
    filmdb.plot = omdb_data['Plot']
    filmdb.save()


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
        _ = ChatClubInfo.objects.create(club=new_club)
        messages.success(self.request, _(f"New club created!"))
        club_member_info = ClubMemberInfo.objects.create(club=new_club, member=user)
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
        context['page'] = 'club_detail'
        club_id = self.kwargs['club_id']
        context = add_club_context(self.request, context, club_id)
        club_meetings = Meeting.objects.filter(club_id=club_id, date__gte=timezone.now().date())
        if club_meetings:
            context['next_meetings'] = club_meetings.order_by('date')[0:3]
            context['extra_meetings'] = len(club_meetings) > 3
        last_comments = FilmComment.objects.filter(club_id=club_id, deleted=False)
        if last_comments:
            context['last_comments'] = last_comments.order_by('-date')[0:5]
        club_films = Film.objects.filter(club_id=club_id)
        if club_films:
            films_last_pub = club_films.order_by('-pub_date')
            groups_last_pub = [films_last_pub[i:i+3] for i in [0, 3, 6, 9]]
            context['groups_last_pub'] = groups_last_pub
            last_seen = club_films.filter(seen=True)
            context['films_last_seen'] = last_seen.order_by('-seen_date')[0:3]
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
        club_member_info = get_object_or_404(ClubMemberInfo, club=club, member=member)
        context['club_member_info'] = club_member_info
        all_votes = member.vote_set.filter(club_id=club.id)
        context['num_of_votes'] = all_votes.count()
        club_films = Film.objects.filter(club_id=club.id)
        club_films_not_seen = club_films.filter(seen=False)
        votes = [vote for vote in all_votes if vote.film in club_films_not_seen]
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
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})


@method_decorator(login_required, name='dispatch')
class EditClubPanelView(UserPassesTestMixin, generic.UpdateView):
    model = Club
    pk_url_kwarg = 'club_id'
    fields = ['panel']

    def test_func(self):
        return user_is_club_admin_check(self.request, self.kwargs['club_id'])

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})


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
            messages.error(request, _("You must promote other club member to admin before leaving the club."))
            return HttpResponseRedirect(reverse_lazy('democracy:club_detail', kwargs={'club_id': club.id}))
        else:
            club.admin_members.remove(user)
    club.members.remove(user)
    club.save()
    club_member_info = get_object_or_404(ClubMemberInfo, club=club, member=user)
    club_member_info.delete()
    messages.success(request, _("Done. You have left the club."))
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
            messages.error(request, _("You must promote other club member to admin before demoting yourself."))
        else:
            club.admin_members.remove(user)
            club.save()
            messages.success(request, _("Done. You have demoted yourself."))
    return HttpResponseRedirect(reverse_lazy('democracy:club_detail', kwargs={'club_id': club.id}))


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
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

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
            club_member_info = get_object_or_404(ClubMemberInfo, club=club, member=member)
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
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

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

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'candidate_films'
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        club_films = Film.objects.filter(club_id=club.id, seen=False)
        view_option = self.kwargs['view_option']
        order_option = self.kwargs['order_option']
        display_option = self.kwargs['display_option']
        context['view_option'] = self.kwargs['view_option']
        context['order_option'] = self.kwargs['order_option']
        context['display_option'] = self.kwargs['display_option']
        if view_option == 'all':
            context['view_option_tag'] = _("All")
        elif view_option == 'not_voted':
            context['view_option_tag'] = _("Not voted")
        elif view_option == 'only_voted':
            context['view_option_tag'] = _("Voted")
        if order_option == 'title':
            context['order_option_string'] = "film.filmdb.title"
            context['order_option_tag'] = _("Title")
        elif order_option == 'date_proposed':
            context['order_option_string'] = "film.pub_date"
            context['order_option_tag'] = _("Proposed")
        elif order_option == 'year':
            context['order_option_string'] = "film.filmdb.year"
            context['order_option_tag'] = _("Year")
        elif order_option == 'duration':
            context['order_option_string'] = "duration"
            context['order_option_tag'] = _("Duration")
        elif order_option == 'user_vote':
            context['order_option_string'] = "vote_points"
            context['order_option_tag'] = _("My vote")
        if display_option == 'posters':
            context['display_option_tag'] = _("Posters")
        elif display_option == 'list':
            context['display_option_tag'] = _("List")
        candidate_films = []
        for film in club_films:
            try:
                film_duration = int(film.filmdb.duration)
            except ValueError:
                if ' min' in film.filmdb.duration:
                    film_duration = int(film.filmdb.duration.replace(' min', ''))
                elif 'min' in film.filmdb.duration:
                    film_duration = int(film.filmdb.duration.replace('min', ''))
                else:
                    film_duration = 0
            film_voters = [vote.user.username for vote in film.vote_set.all()]
            if self.request.user.username in film_voters:
                if view_option == 'all' or view_option == 'only_voted':
                    user_vote = get_object_or_404(Vote, user=self.request.user, film=film)
                    candidate_films.append({
                        'film': film,
                        'voted': True,
                        'vote_points': - user_vote.vote_score,
                        'duration': film_duration,
                        'vote': user_vote.vote_karma,
                    })
            elif view_option != 'only_voted':
                candidate_films.append({
                    'film': film,
                    'voted': False,
                    'vote_points': -2.5,
                    'duration': film_duration,
                    'vote': False,
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


@login_required
def add_new_film(request, club_id, view_option, order_option, display_option):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    imdb_url = request.POST.get('imdb_url')
    try:
        if 'imdb' not in imdb_url:
            raise ValueError
        url_list = imdb_url.split('/')
        title_position = url_list.index('title')
        imdb_key = url_list[title_position + 1]
        if 'tt' not in imdb_key or len(imdb_key) is not 9:
            raise ValueError
        else:
            imdb_id = imdb_key.replace('tt', '')
            if Film.objects.filter(club=club_id, imdb_id=imdb_id, seen=False):
                raise KeyError
            else:
                filmdb, created = FilmDb.objects.get_or_create(imdb_id=imdb_id)
                if created or (not created and not filmdb.title):
                    update_filmdb_omdb_info(filmdb, imdb_id)
                club = get_object_or_404(Club, pk=club_id)
                new_film_id = random_id_generator(club_id)
                film = Film.objects.create(
                    id=f'{club_id}{new_film_id}',
                    imdb_id=imdb_id,
                    proposed_by=request.user,
                    club=club,
                    filmdb=filmdb,
                )
                film.save()
                messages.success(request, _('New film added! Be the first to vote it!'))
                return HttpResponseRedirect(reverse(
                    'democracy:film_detail',
                    kwargs={'club_id': club_id,
                            'film_id': film.id,
                            'view_option': view_option,
                            'order_option': order_option,
                            'display_option': display_option}
                ))
    except ValueError:
        messages.warning(request, _('The IMDb url does not seem to be valid.'))
    except KeyError:
        messages.warning(request, _("That film is already in the candidate list!"))
    return HttpResponseRedirect(reverse(
        'democracy:candidate_films',
        kwargs={'club_id': club_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@method_decorator(login_required, name='dispatch')
class FilmDetailView(UserPassesTestMixin, generic.TemplateView):
    model = Film

    @staticmethod
    def choice_karma_dict(vote_choice):
        vote_karma_dict = {
            Vote.OMG: 'positive',
            Vote.YES: 'positive',
            Vote.SEENOK: 'positive',
            Vote.MEH: 'positive',
            Vote.NO: 'negative',
            Vote.SEENNO: 'negative',
            Vote.VETO: 'negative',
        }
        return vote_karma_dict[vote_choice]

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = add_club_context(self.request, context, self.kwargs['club_id'])
        context['page'] = 'film_detail'
        context['view_option'] = self.kwargs['view_option']
        context['order_option'] = self.kwargs['order_option']
        context['display_option'] = self.kwargs['display_option']
        film = get_object_or_404(Film, pk=self.kwargs['film_id'])
        context['film'] = film
        context['updatable_db'] = film.filmdb.updatable
        try:
            context['film_duration'] = f'{int(film.filmdb.duration)} min'
        except ValueError:
            if ' min' in film.filmdb.duration:
                context['film_duration'] = film.filmdb.duration
            elif 'min' in film.filmdb.duration:
                context['film_duration'] = film.filmdb.duration.replace('min', ' min')
            else:
                context['film_duration'] = film.filmdb.duration
        film_comments = FilmComment.objects.filter(club=self.kwargs['club_id'], film=self.kwargs['film_id'])
        context['film_comments'] = film_comments.order_by('date')
        choice_dict = {}
        for choice in Vote.vote_choices:
            choice_dict[choice[0]] = {
                'choice': choice[0],
                'choice_text': choice[1],
                'choice_karma': self.choice_karma_dict(choice[0]),
                'choice_voted': False,
            }
        try:
            user_vote = Vote.objects.get(user=self.request.user, film=film)
            context['film_voted'] = True
            choice_dict[user_vote.choice]['choice_voted'] = True
        except Vote.DoesNotExist:
            context['film_voted'] = False
        context['vote_choices'] = choice_dict
        return context


@login_required
def vote_film(request, club_id, film_id, view_option, order_option, display_option):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    user_vote, _ = Vote.objects.get_or_create(user=request.user, film=film, club=club)
    user_vote.choice = request.POST['choice']
    user_vote.save()
    return HttpResponseRedirect(reverse(
        'democracy:candidate_films',
        kwargs={'club_id': club_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def delete_vote(request, club_id, film_id, view_option, order_option, display_option):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    vote = get_object_or_404(Vote, user=request.user, film=film, club=club)
    vote.delete()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'club_id': club_id,
                'film_id': film_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def comment_film(request, club_id, film_id, view_option, order_option, display_option):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    comment_text = request.POST['text']
    if not comment_text == '':
        film_comment = FilmComment.objects.create(user=request.user, film=film, club=club, text=comment_text)
        film_comment.save()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'club_id': club_id,
                'film_id': film_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def delete_film_comment(request, club_id, film_id, comment_id, view_option, order_option, display_option):
    film_comment = get_object_or_404(FilmComment, id=comment_id)
    if request.user != film_comment.user:
        if not user_is_club_admin_check(request, club_id):
            return HttpResponseForbidden()
    film_comment.deleted = True
    film_comment.save()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'club_id': club_id,
                'film_id': film_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def add_filmaffinity_url(request, club_id, film_id, view_option, order_option, display_option):
    faff_url = request.POST.get('faff_url')
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    try:
        if 'filmaffinity' not in faff_url:
            raise ValueError
        elif 'm.filmaffinity' in faff_url:
            try:
                filmaff_key = faff_url.split('id=')[1][0:6]
            except IndexError:
                raise ValueError
        else:
            try:
                filmaff_key = faff_url.split('film')[2][0:6]
            except IndexError:
                raise ValueError
            if '.html' in filmaff_key:
                filmaff_key = filmaff_key.replace('.html', '')
        if len(filmaff_key) is not 6:
            raise ValueError
        film = get_object_or_404(Film, pk=film_id)
        filmdb = get_object_or_404(FilmDb, imdb_id=film.filmdb.imdb_id)
        filmdb.faff_id = filmaff_key
        filmdb.save()
        messages.success(request, _('Link to FilmAffinity added!'))
    except ValueError:
        messages.warning(request, _('Invalid FilmAffinity url!'))
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'club_id': club_id,
                'film_id': film_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@method_decorator(login_required, name='dispatch')
class FilmSeenView(UserPassesTestMixin, generic.FormView):
    form_class = forms.FilmSeenForm

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_success_url(self):
        return reverse_lazy(
            'democracy:film_detail',
            kwargs={'club_id': self.kwargs['club_id'],
                    'film_id': self.kwargs['film_id'],
                    'view_option': 'all',
                    'order_option': 'title',
                    'display_option': 'posters'}
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
def delete_film(request, club_id, film_id, view_option, order_option, display_option):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    film.delete()
    return HttpResponseRedirect(reverse(
        'democracy:candidate_films',
        kwargs={'club_id': club_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def unsee_film(request, club_id, film_id, view_option, order_option, display_option):
    if not user_is_club_admin_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    if Film.objects.filter(club=club_id, imdb_id=film.filmdb.imdb_id, seen=False):
        messages.warning(request, _('This film is already in the candidate list! Delete it or leave it.'))
        return HttpResponseRedirect(reverse(
            'democracy:film_detail',
            kwargs={'club_id': club_id,
                    'film_id': film_id,
                    'view_option': view_option,
                    'order_option': order_option,
                    'display_option': display_option}
        ))
    else:
        film.seen = False
        film.seen_by.clear()
        film.seen_date = None
        film.save()
        return HttpResponseRedirect(reverse(
            'democracy:candidate_films',
            kwargs={'club_id': club_id,
                    'view_option': view_option,
                    'order_option': order_option,
                    'display_option': display_option}
        ))


@login_required
def update_film_data(request, club_id, film_id, view_option, order_option, display_option):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    filmdb = get_object_or_404(FilmDb, pk=film.filmdb.imdb_id)
    if filmdb.updatable:
        update_filmdb_omdb_info(filmdb, filmdb.imdb_id)
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'club_id': club_id,
                'film_id': film_id,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@method_decorator(login_required, name='dispatch')
class ParticipantsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'film_ranking'
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

        def process_film(film, participants):
            warnings = []
            film_all_votes = film.vote_set.all()
            film_voters = [vote.user for vote in film_all_votes]
            abstentionists = []
            positive_votes = []
            negative_votes = []
            for participant in participants:
                if participant not in film_voters:
                    abstentionists.append(participant)
            film_votes = []
            for vote in film_all_votes:
                if vote.user in participants:
                    film_votes.append(vote.choice)
                    if vote.vote_karma is 'positive':
                        positive_votes.append(vote)
                    elif vote.vote_karma is 'negative':
                        negative_votes.append(vote)
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
            votes_info = (positive_votes, negative_votes, abstentionists)

            # TODO: use aggregations to do this count
            n_veto = film_votes.count(Vote.VETO)
            n_seenno = film_votes.count(Vote.SEENNO)
            n_no = film_votes.count(Vote.NO)
            n_meh = film_votes.count(Vote.MEH)
            n_seenok = film_votes.count(Vote.SEENOK)
            n_yes = film_votes.count(Vote.YES)
            n_omg = film_votes.count(Vote.OMG)
            if n_veto >= 1:
                return votes_info, warnings, -10000, True
            else:
                points = (
                        - 50 * n_seenno
                        - 25 * n_no
                        + 0 * n_meh
                        + 5 * n_seenok
                        + 10 * n_yes
                        + 20 * n_omg
                )
                return votes_info, warnings, points, False

        films_results = []
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        participants = [get_object_or_404(User, id=id) for id in self.request.GET.getlist('participants')]
        exclude_not_present = self.request.GET.get('exclude_not_present')
        max_duration_input = self.request.GET.get('max_duration')
        if max_duration_input == '':
            max_duration = 999
        else:
            try:
                max_duration = int(max_duration_input)
            except ValueError:
                messages.warning(self.request, _('Invalid maximum film duration input! Filter not applied.'))
                max_duration = 999
        club_films = Film.objects.filter(club_id=club.id, seen=False)
        for film in club_films:
            if not(film.proposed_by not in participants and exclude_not_present):
                try:
                    film_duration = int(film.filmdb.duration)
                except ValueError:
                    if ' min' in film.filmdb.duration:
                        film_duration = int(film.filmdb.duration.replace(' min', ''))
                    elif 'min' in film.filmdb.duration:
                        film_duration = int(film.filmdb.duration.replace('min', ''))
                    else:
                        film_duration = film.filmdb.duration
                if isinstance(film_duration, int) and film_duration > max_duration:
                    continue
                else:
                    votes_info, warnings, points, veto = process_film(film, participants)
                    if film.proposed_by not in participants:
                        warnings.append({
                            'type': 'proposer missing',
                            'film': film.filmdb.title,
                            'voter': film.proposed_by.username,
                        })
                    films_results.append({
                        'id': film.id,
                        'title': film.filmdb.title,
                        'duration': f'{film_duration} min',
                        'positive_votes': votes_info[0],
                        'negative_votes': votes_info[1],
                        'abstentionists': votes_info[2],
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
    form_class = forms.InviteNewMemberForm
    subject_template_name = 'democracy/emails/invite_new_member_subject.txt'
    email_template_name = 'democracy/emails/invite_new_member_email.html'
    html_email_template_name = 'democracy/emails/invite_new_member_email_html.html'
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
        messages.success(self.request, _('An invitation email has been sent to: ') + form.cleaned_data['email'] + '!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

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
        email = str(urlsafe_base64_decode(self.kwargs['uemailb64']), 'utf-8')
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
            uobjectid = str(urlsafe_base64_decode(uobjectidb64), 'utf-8')
            object = object_model.objects.get(pk=int(uobjectid))
        except (TypeError, ValueError, OverflowError, object_model.DoesNotExist, ValidationError):
            object = None
        return object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.validlink:
            club = self.get_object(Club, self.kwargs['uclubidb64'])
            context['validlink'] = True
            context['club'] = club
        else:
            context.update({'form': None, 'validlink': False})
        return context

    def form_valid(self, form):
        user = self.request.user
        club = self.get_object(Club, self.kwargs['uclubidb64'])
        club_members = club.members.filter(is_active=True)
        if user not in club_members:
            club.members.add(self.request.user)
            club.save()
            club_member_info = ClubMemberInfo.objects.create(club=club, member=user)
            club_member_info.save()
        messages.success(self.request, _('Congratulations! You have are now a proud member of the club!'))
        return super().form_valid(form)

    def get_success_url(self):
        club = self.get_object(Club, self.kwargs['uclubidb64'])
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': club.id})


@method_decorator(login_required, name='dispatch')
class MeetingsNewView(UserPassesTestMixin, generic.FormView):
    form_class = forms.MeetingsForm
    subject_template_name = 'democracy/emails/meetings_new_subject.txt'
    email_template_name = 'democracy/emails/meetings_new_email.html'
    html_email_template_name = 'democracy/emails/meetings_new_email_html.html'
    extra_email_context = None
    from_email = 'filmdemocracyweb@gmail.com'

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_form_kwargs(self):
        kwargs = super(MeetingsNewView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['new_meeting'] = True
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
        if form.cleaned_data['send_spam']:
            email_opts = {
                'domain_override': None,
                'subject_template_name': self.subject_template_name,
                'email_template_name': self.email_template_name,
                'html_email_template_name': self.html_email_template_name,
                'extra_email_context': self.extra_email_context,
                'use_https': self.request.is_secure(),
                'from_email': self.from_email,
                'request': self.request,
            }
            spammable_members = club.members.filter(is_active=True)
            form.spam_members(spammable_members, **email_opts)
            messages.success(self.request, _('Meeting planned! A notification has been sent to club members.'))
        else:
            messages.success(self.request, _('Meeting planned!'))
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class MeetingsEditView(UserPassesTestMixin, generic.FormView):
    form_class = forms.MeetingsForm
    subject_template_name = 'democracy/emails/meetings_edit_subject.txt'
    email_template_name = 'democracy/emails/meetings_edit_email.html'
    html_email_template_name = 'democracy/emails/meetings_edit_email_html.html'
    extra_email_context = None
    from_email = 'filmdemocracyweb@gmail.com'

    def test_func(self):
        return user_is_organizer_check(
            self.request,
            self.kwargs['club_id'],
            self.kwargs['meeting_id']
        )

    def get_form_kwargs(self):
        kwargs = super(MeetingsEditView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        kwargs.update({'meeting_id': self.kwargs['meeting_id']})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['meeting'] = get_object_or_404(Meeting, pk=self.kwargs['meeting_id'])
        context['new_meeting'] = False
        return context

    def form_valid(self, form):
        meeting = get_object_or_404(Meeting, pk=self.kwargs['meeting_id'])
        meeting.name = form.cleaned_data['name']
        meeting.description = form.cleaned_data['description']
        meeting.place = form.cleaned_data['place']
        meeting.date = form.cleaned_data['date']
        meeting.time_start = form.cleaned_data['time_start']
        meeting.time_end = form.cleaned_data['time_end']
        meeting.save()
        spam_opt = form.cleaned_data['spam_opts']
        if spam_opt == 'all' or spam_opt == 'interested':
            email_opts = {
                'domain_override': None,
                'subject_template_name': self.subject_template_name,
                'email_template_name': self.email_template_name,
                'html_email_template_name': self.html_email_template_name,
                'extra_email_context': self.extra_email_context,
                'use_https': self.request.is_secure(),
                'from_email': self.from_email,
                'request': self.request,
            }
            if spam_opt == 'all':
                club = get_object_or_404(Club, pk=self.kwargs['club_id'])
                spammable_members = club.members.filter(is_active=True)
                form.spam_members(spammable_members, **email_opts)
                messages.success(self.request, _('Meeting edited! A notification has been sent to club members.'))
            elif spam_opt == 'interested':
                meeting_members = [meeting.members_yes.all(), meeting.members_maybe.all(), meeting.members_no.all()]
                for spammable_members in meeting_members:
                    form.spam_members(spammable_members, **email_opts)
                messages.success(
                    self.request,
                    _('Meeting edited! A notification has been sent to members interested in it.')
                )
        else:
            messages.success(self.request, _('Meeting edited!'))
        return super().form_valid(form)


@login_required
def meeting_assistance(request, club_id, meeting_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    user = request.user
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    if 'assist_yes' in request.POST:
        if user in meeting.members_yes.all():
            meeting.members_yes.remove(user)
        else:
            if user in meeting.members_maybe.all():
                meeting.members_maybe.remove(user)
            elif user in meeting.members_no.all():
                meeting.members_no.remove(user)
            meeting.members_yes.add(user)
    elif 'assist_maybe' in request.POST:
        if user in meeting.members_maybe.all():
            meeting.members_maybe.remove(user)
        else:
            if user in meeting.members_yes.all():
                meeting.members_yes.remove(user)
            elif user in meeting.members_no.all():
                meeting.members_no.remove(user)
            meeting.members_maybe.add(user)
    elif 'assist_no' in request.POST:
        if user in meeting.members_no.all():
            meeting.members_no.remove(user)
        else:
            if user in meeting.members_yes.all():
                meeting.members_yes.remove(user)
            if user in meeting.members_maybe.all():
                meeting.members_maybe.remove(user)
            meeting.members_no.add(user)
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
    return HttpResponseRedirect(reverse('democracy:club_detail', kwargs={'club_id': club_id}))


@method_decorator(login_required, name='dispatch')
class MeetingsListView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = add_club_context(self.request, context, self.kwargs['club_id'])
        club_meetings = Meeting.objects.filter(club_id=self.kwargs['club_id'], date__gte=timezone.now().date())
        context['club_meetings'] = club_meetings.order_by('date')
        return context


@method_decorator(login_required, name='dispatch')
class ChatClubView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'chat'
        context = add_club_context(self.request, context, self.kwargs['club_id'])
        posts = ChatClubPost.objects.filter(club=self.kwargs['club_id'])
        context['posts'] = posts.order_by('-date')[:1000]  # TODO
        return context


@login_required
def post_in_chatclub(request, club_id):
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    club = get_object_or_404(Club, pk=club_id)
    post_text = request.POST['text']
    if not post_text.lstrip() == '':
        post = ChatClubPost.objects.create(user_sender=request.user, club=club, text=post_text)
        post.save()
        chat_info, _ = ChatClubInfo.objects.get_or_create(club=club)  # TODO: change to get_or_404 in pro version
        chat_info.last_post = post
        chat_info.save()
    return HttpResponseRedirect(reverse('democracy:chatclub', kwargs={'club_id': club_id}))


@login_required
def delete_chatclub_post(request, club_id, post_id):
    post = get_object_or_404(ChatClubPost, id=post_id)
    if request.user != post.user:
        if not user_is_club_admin_check(request, club_id):
            return HttpResponseForbidden()
    post.deleted = True
    post.save()
    return HttpResponseRedirect(reverse('democracy:chatclub', kwargs={'club_id': club_id}))


@method_decorator(login_required, name='dispatch')
class ChatContactsView(generic.TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_clubs = user.club_set.all()
        unique_contacts = []
        for club in user_clubs:
            for contact in club.members.filter(is_active=True).exclude(pk=self.request.user.id):
                unique_contacts.append(contact)
        unique_contacts = set(unique_contacts)
        contacts_info = []
        for contact in unique_contacts:
            common_clubs = []
            for club in user_clubs:
                if contact in club.members.filter(is_active=True):
                    common_clubs.append(club)
            contacts_info.append({
                'contact': contact,
                'common_clubs': common_clubs
            })
            context['contacts_info'] = contacts_info
        return context


@method_decorator(login_required, name='dispatch')
class ChatUsersView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return users_know_each_other_check(self.request, self.kwargs['chatuser_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'chat'
        chat_user = get_object_or_404(User, pk=self.kwargs['chatuser_id'])
        context['chat_user'] = chat_user
        posts_a = ChatUsersPost.objects.filter(user_sender=self.request.user, user_receiver=chat_user)
        posts_b = ChatUsersPost.objects.filter(user_sender=chat_user, user_receiver=self.request.user)
        posts = posts_a | posts_b
        context['posts'] = posts.order_by('-date')[:1000]
        return context


@login_required
def post_in_chatusers(request, chatuser_id):
    if not users_know_each_other_check(request, chatuser_id):
        return HttpResponseForbidden()
    chat_user = get_object_or_404(User, pk=chatuser_id)
    post_text = request.POST['text']
    if not post_text.lstrip() == '':
        post = ChatUsersPost.objects.create(user_sender=request.user, user_receiver=chat_user, text=post_text)
        post.save()
        for users_tuple in [(request.user, chat_user), (chat_user, request.user)]:
            chat_info, _ = ChatUsersInfo.objects.get_or_create(user=users_tuple[0], user_known=users_tuple[1])
            chat_info.last_post = post
            chat_info.save()
    return HttpResponseRedirect(reverse('democracy:chatusers', kwargs={'chatuser_id': chatuser_id}))


@login_required
def delete_chatusers_post(request, post_id):
    post = get_object_or_404(ChatUsersPost, id=post_id)
    if request.user != post.user:
        return HttpResponseForbidden()
    post.deleted = True
    post.save()
    return HttpResponseRedirect(reverse('democracy:chatusers', kwargs={'chatuser_id': post.user_receiver.id}))
