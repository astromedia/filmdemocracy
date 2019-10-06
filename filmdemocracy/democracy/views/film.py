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
from filmdemocracy.democracy.models import Club, Notification, ClubMemberInfo, InvitationLink
from filmdemocracy.democracy.models import ChatClubPost, ChatUsersPost, ChatUsersInfo, ChatClubInfo, Meeting
from filmdemocracy.democracy.models import FilmDb, Film, Vote, FilmComment
from filmdemocracy.registration.models import User

from filmdemocracy.utils import user_is_club_member_check, user_is_club_admin_check, user_is_organizer_check, users_know_each_other_check
from filmdemocracy.utils import add_club_context, update_filmdb_omdb_info, extract_club_id
from filmdemocracy.utils import random_club_id_generator, random_film_id_generator, random_meeting_id_generator
from filmdemocracy.utils import NotificationsHelper
from filmdemocracy.utils import RankingGenerator


@method_decorator(login_required, name='dispatch')
class FilmDetailView(UserPassesTestMixin, generic.TemplateView):
    model = Film

    @staticmethod
    def choice_karma_mapper(vote_choice):
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
        club_id = extract_club_id(self.kwargs['film_id'])
        return user_is_club_member_check(self.request, club_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = extract_club_id(self.kwargs['film_id'])
        context = add_club_context(self.request, context, club_id)
        context['page'] = 'film_detail'
        context['view_option'] = self.kwargs['view_option'] if 'view_option' in self.kwargs else 'all'
        context['order_option'] = self.kwargs['order_option'] if 'order_option' in self.kwargs else 'title'
        context['display_option'] = self.kwargs['display_option'] if 'display_option' in self.kwargs else 'posters'
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
        film_comments = FilmComment.objects.filter(club=club_id, film=self.kwargs['film_id'])
        context['film_comments'] = film_comments.order_by('datetime')
        choice_dict = {}
        for choice in Vote.vote_choices:
            choice_dict[choice[0]] = {
                'choice': choice[0],
                'choice_text': choice[1],
                'choice_karma': self.choice_karma_mapper(choice[0]),
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
def vote_film(request, film_id, view_option='all', order_option='title', display_option='posters'):
    club_id = extract_club_id(film_id)
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    user_vote, tmp = Vote.objects.get_or_create(user=request.user, film=film, club=club)
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
def delete_vote(request, film_id, view_option='all', order_option='title', display_option='posters'):
    club_id = extract_club_id(film_id)
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    vote = get_object_or_404(Vote, user=request.user, film=film, club=club)
    vote.delete()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'film_id': film.id,
                'film_slug': film.filmdb.slug,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def comment_film(request, film_id, view_option='all', order_option='title', display_option='posters'):

    def create_notifications(_user, _club, _film):
        proposer = _film.proposed_by
        film_commenters = [fc.user for fc in FilmComment.objects.filter(film=_film, deleted=False)]

        # Notification to film proposer:
        if _user != proposer:
            Notification.objects.create(type=Notification.COMM_FILM,
                                        activator=_user,
                                        club=_club,
                                        object_film=_film,
                                        recipient=proposer)

        # Notifications to people that commented on that film before (film_commenters):
        for commenter in film_commenters:
            if commenter != proposer and commenter != _user:
                Notification.objects.create(type=Notification.COMM_COMM,
                                            activator=_user,
                                            club=_club,
                                            recipient=commenter,
                                            object_film=_film)

    club_id = extract_club_id(film_id)
    if not user_is_club_member_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    club = get_object_or_404(Club, pk=club_id)
    comment_text = request.POST['text']
    if not comment_text == '':
        film_comment = FilmComment.objects.create(user=request.user, film=film, club=club, text=comment_text)
        film_comment.save()
        create_notifications(request.user, club, film)
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'film_id': film.id,
                'film_slug': film.filmdb.slug,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def delete_film_comment(request, film_id, comment_id, view_option='all', order_option='title', display_option='posters'):
    club_id = extract_club_id(film_id)
    film = get_object_or_404(Film, pk=film_id)
    film_comment = get_object_or_404(FilmComment, id=comment_id)
    if request.user != film_comment.user:
        if not user_is_club_admin_check(request, club_id):
            return HttpResponseForbidden()
    film_comment.deleted = True
    film_comment.save()
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'film_id': film.id,
                'film_slug': film.filmdb.slug,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@login_required
def add_filmaffinity_url(request, film_id, view_option='all', order_option='title', display_option='posters'):
    club_id = extract_club_id(film_id)
    film = get_object_or_404(Film, pk=film_id)
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
        filmdb = get_object_or_404(FilmDb, imdb_id=film.filmdb.imdb_id)
        filmdb.faff_id = filmaff_key
        filmdb.save()
        messages.success(request, _('Link to FilmAffinity added!'))
    except ValueError:
        messages.error(request, _('Invalid FilmAffinity url!'))
    return HttpResponseRedirect(reverse(
        'democracy:film_detail',
        kwargs={'film_id': film.id,
                'film_slug': film.filmdb.slug,
                'view_option': view_option,
                'order_option': order_option,
                'display_option': display_option}
    ))


@method_decorator(login_required, name='dispatch')
class FilmSeenView(UserPassesTestMixin, generic.FormView):
    form_class = forms.FilmSeenForm

    def test_func(self):
        club_id = extract_club_id(self.kwargs['film_id'])
        return user_is_club_member_check(self.request, club_id)

    def get_success_url(self):
        film = get_object_or_404(Film, pk=self.kwargs['film_id'])
        return reverse_lazy(
            'democracy:film_detail',
            kwargs={'film_id': film.id,
                    'film_slug': film.filmdb.slug,
                    'view_option': self.kwargs['view_option'] if 'view_option' in self.kwargs else 'all',
                    'order_option': self.kwargs['order_option'] if 'order_option' in self.kwargs else 'title',
                    'display_option': self.kwargs['display_option'] if 'display_option' in self.kwargs else 'posters'}
        )

    def get_form_kwargs(self):
        kwargs = super(FilmSeenView, self).get_form_kwargs()
        kwargs.update({'film_id': self.kwargs['film_id']})
        club_id = extract_club_id(self.kwargs['film_id'])
        club = get_object_or_404(Club, pk=club_id)
        kwargs.update({'club_members': club.members.filter(is_active=True)})
        return kwargs

    @staticmethod
    def create_notifications(user, club, film):
        club_members = club.members.filter(is_active=True).exclude(pk=user.id)
        for member in club_members:
            Notification.objects.create(type=Notification.SEEN_FILM,
                                        activator=user,
                                        club=club,
                                        recipient=member,
                                        object_film=film)

    def form_valid(self, form):
        club_id = extract_club_id(self.kwargs['film_id'])
        club = get_object_or_404(Club, pk=club_id)
        film = get_object_or_404(Film, id=self.kwargs['film_id'])
        film.seen_date = form.cleaned_data['seen_date']
        members = form.cleaned_data['members']
        for member in members:
            film.seen_by.add(member)
        film.seen = True
        film.save()
        self.create_notifications(self.request.user, club, film)
        messages.success(self.request, _('Film marked as seen.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = extract_club_id(self.kwargs['film_id'])
        context['film'] = get_object_or_404(Film, pk=self.kwargs['film_id'])
        club = get_object_or_404(Club, pk=club_id)
        context['club'] = club
        context['club_members'] = club.members.filter(is_active=True)
        return context


@login_required
def delete_film(request, film_id, view_option='all', order_option='title', display_option='posters'):
    club_id = extract_club_id(film_id)
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
def unsee_film(request, film_id, view_option='all', order_option='title', display_option='posters'):
    club_id = extract_club_id(film_id)
    if not user_is_club_admin_check(request, club_id):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=film_id)
    if Film.objects.filter(club=club_id, imdb_id=film.filmdb.imdb_id, seen=False):
        messages.error(request, _('This film is already in the candidate list! Delete it or leave it.'))
        return HttpResponseRedirect(reverse(
            'democracy:film_detail',
            kwargs={'film_id': film.id,
                    'film_slug': film.filmdb.slug,
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
