from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic

from filmdemocracy.democracy import forms
from filmdemocracy.core.models import Notification
from filmdemocracy.democracy.models import FilmDb, Film, Vote, FilmComment, Club

from filmdemocracy.core.utils import user_is_club_member_check, user_is_club_admin_check
from filmdemocracy.core.utils import extract_options


@method_decorator(login_required, name='dispatch')
class FilmDetailView(UserPassesTestMixin, generic.TemplateView):
    model = Film

    @staticmethod
    def choice_karma_mapper(vote_choice):
        vote_karma_dict = {
            Vote.OMG: 'positive',
            Vote.YES: 'positive',
            Vote.SEENOK: 'positive',
            Vote.MEH: 'neutral',
            Vote.NO: 'negative',
            Vote.SEENNO: 'negative',
            Vote.VETO: 'negative',
        }
        return vote_karma_dict[vote_choice]

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        film = get_object_or_404(Film, club=club, public_id=self.kwargs['film_public_id'])
        context['page'] = 'film_detail'
        options_string = self.kwargs['options_string'] if 'options_string' in self.kwargs and self.kwargs['options_string'] else None
        view_option, order_option, display_option = extract_options(options_string)
        context['view_option'] = view_option
        context['order_option'] = order_option
        context['display_option'] = display_option
        context['film'] = film
        context['updatable_db'] = film.db.updatable
        context['film_duration'] = film.db.duration_str
        film_comments = FilmComment.objects.filter(club=club.id, film=film)
        context['film_comments'] = film_comments.order_by('created_datetime')
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
            context['user_vote'] = user_vote
            choice_dict[user_vote.choice]['choice_voted'] = True
        except Vote.DoesNotExist:
            context['user_vote'] = None
        context['vote_choices'] = choice_dict
        return context


@method_decorator(login_required, name='dispatch')
class FilmSeenView(UserPassesTestMixin, generic.FormView):
    form_class = forms.FilmSeenForm

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_success_url(self):
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        film = get_object_or_404(Film, club=club, public_id=self.kwargs['film_public_id'])
        return reverse('democracy:film_detail', kwargs={'club_id': club.id,
                                                        'film_public_id': film.public_id,
                                                        'film_slug': film.db.slug,
                                                        'options_string': self.kwargs['options_string']})

    def get_form_kwargs(self):
        kwargs = super(FilmSeenView, self).get_form_kwargs()
        kwargs.update({'film_public_id': self.kwargs['film_public_id']})
        kwargs.update({'club_id': self.kwargs['club_id']})
        return kwargs

    @staticmethod
    def create_notifications(_user, _club, _film):
        club_members = _club.members.filter(is_active=True).exclude(id=_user.id)
        for member in club_members:
            Notification.objects.create(type=Notification.SEEN_FILM,
                                        activator=_user,
                                        club=_club,
                                        recipient=member,
                                        object_id=_film.id)

    def form_valid(self, form):
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        film = get_object_or_404(Film, club=club, public_id=self.kwargs['film_public_id'])
        film.seen_date = form.cleaned_data['seen_date']
        members = form.cleaned_data['members']
        for member in members:
            film.seen_by.add(member)
        film.seen = True
        film.marked_seen_by = self.request.user
        film.save()
        self.create_notifications(self.request.user, club, film)
        messages.success(self.request, _('Film marked as seen.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        film = get_object_or_404(Film, club=club, public_id=self.kwargs['film_public_id'])
        context['film'] = film
        return context


@login_required
def vote_film(request, club_id, film_public_id, options_string):
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(request.user, club=club):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, club=club, public_id=film_public_id)
    user_vote, tmp = Vote.objects.get_or_create(user=request.user, film=film, club=club)
    user_vote.choice = request.POST['choice']
    user_vote.save()
    return HttpResponseRedirect(reverse('democracy:candidate_films', kwargs={'club_id': club.id,
                                                                             'options_string': options_string}))


@login_required
def delete_vote(request, club_id, film_public_id, options_string):
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(request.user, club=club):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, club=club, public_id=film_public_id)
    vote = get_object_or_404(Vote, user=request.user, film=film, club=club)
    vote.delete()
    return HttpResponseRedirect(reverse('democracy:film_detail', kwargs={'club_id': club.id,
                                                                         'film_public_id': film.public_id,
                                                                         'film_slug': film.db.slug,
                                                                         'options_string': options_string}))


@login_required
def comment_film(request, club_id, film_public_id, options_string):

    def create_notifications(_user, _club, _film):
        proposer = _film.proposed_by
        film_commenters = [fc.user for fc in FilmComment.objects.filter(film=_film, deleted=False)]

        # Notification to film proposer:
        if _user != proposer:
            Notification.objects.create(type=Notification.COMM_FILM,
                                        activator=_user,
                                        club=_club,
                                        object_id=_film.id,
                                        recipient=proposer)

        # Notifications to people that commented on that film before (film_commenters):
        for commenter in film_commenters:
            if commenter != proposer and commenter != _user:
                Notification.objects.create(type=Notification.COMM_COMM,
                                            activator=_user,
                                            club=_club,
                                            recipient=commenter,
                                            object_id=_film.id)

    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(request.user, club=club):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, club=club, public_id=film_public_id)
    comment_text = request.POST['text']
    if not comment_text == '':
        film_comment = FilmComment.objects.create(user=request.user, film=film, club=club, text=comment_text)
        film_comment.save()
        create_notifications(request.user, club, film)
    return HttpResponseRedirect(reverse('democracy:film_detail', kwargs={'club_id': club.id,
                                                                         'film_public_id': film.public_id,
                                                                         'film_slug': film.db.slug,
                                                                         'options_string': options_string}))


@login_required
def delete_film_comment(request, club_id, film_public_id, comment_id, options_string):
    club = get_object_or_404(Club, id=club_id)
    film = get_object_or_404(Film, club=club, public_id=film_public_id)
    film_comment = get_object_or_404(FilmComment, id=comment_id)
    if request.user != film_comment.user:
        if not user_is_club_admin_check(request.user, club=club):
            return HttpResponseForbidden()
    film_comment.deleted = True
    film_comment.save()
    return HttpResponseRedirect(reverse('democracy:film_detail', kwargs={'club_id': club.id,
                                                                         'film_public_id': film.public_id,
                                                                         'film_slug': film.db.slug,
                                                                         'options_string': options_string}))


@login_required
def add_filmaffinity_url(request, club_id, film_public_id, options_string):
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(request.user, club=club):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, club=club, public_id=film_public_id)
    faff_url = request.POST.get('faff_url')
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
        filmdb = get_object_or_404(FilmDb, imdb_id=film.db.imdb_id)
        filmdb.faff_id = filmaff_key
        filmdb.save()
        messages.success(request, _('Link to FilmAffinity added!'))
    except ValueError:
        messages.error(request, _('Invalid FilmAffinity url!'))
    return HttpResponseRedirect(reverse('democracy:film_detail', kwargs={'club_id': club.id,
                                                                         'film_public_id': film.public_id,
                                                                         'film_slug': film.db.slug,
                                                                         'options_string': options_string}))


@login_required
def delete_film(request, club_id, film_public_id, options_string):
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(request.user, club=club):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, club=club, public_id=film_public_id)
    film.delete()
    return HttpResponseRedirect(reverse('democracy:candidate_films', kwargs={'club_id': club.id,
                                                                             'options_string': options_string}))


@login_required
def unsee_film(request, club_id, film_public_id, options_string):
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_admin_check(request.user, club=club):
        return HttpResponseForbidden()
    film = get_object_or_404(Film, club=club, public_id=film_public_id)
    if Film.objects.filter(club=club_id, db=film.db, seen=False):
        messages.error(request, _('This film is already in the candidate list! Delete it or leave it.'))
        return HttpResponseRedirect(reverse('democracy:film_detail', kwargs={'club_id': club.id,
                                                                             'film_public_id': film.public_id,
                                                                             'film_slug': film.db.slug,
                                                                             'options_string': options_string}))
    else:
        film.seen = False
        film.seen_by.clear()
        film.seen_date = None
        film.save()
        return HttpResponseRedirect(reverse('democracy:candidate_films', kwargs={'club_id': club.id,
                                                                                 'options_string': options_string}))