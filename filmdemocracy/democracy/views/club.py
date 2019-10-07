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
from filmdemocracy.utils import add_club_context, update_filmdb_omdb_info
from filmdemocracy.utils import random_club_id_generator, random_film_id_generator, random_meeting_id_generator
from filmdemocracy.utils import NotificationsHelper
from filmdemocracy.utils import RankingGenerator


@method_decorator(login_required, name='dispatch')
class CreateClubView(generic.FormView):
    form_class = forms.EditClubForm

    def get_success_url(self):
        # TODO: redirect to club view
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.new_club.id})

    def form_valid(self, form):
        user = self.request.user
        new_club = Club.objects.create(
            id=random_club_id_generator(),
            name=form.cleaned_data['name'],
            short_description=form.cleaned_data['short_description'],
            logo=form.cleaned_data['logo'],
        )
        new_club.admin_members.add(user)
        new_club.members.add(user)
        new_club.save()
        self.new_club = new_club
        ChatClubInfo.objects.create(club=new_club)
        messages.success(self.request, _(f"New club created! Now you can invite people to your club, "
                                         f"propose films, and organize meetings."))
        ClubMemberInfo.objects.create(club=new_club, member=user)
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
            context['last_comments'] = last_comments.order_by('-datetime')[0:5]
        club_films = Film.objects.filter(club_id=club_id)
        if club_films:
            films_last_pub = club_films.order_by('-pub_datetime')
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
    Notification.objects.filter(club=club, recipient=user).delete()
    club_member_info = get_object_or_404(ClubMemberInfo, club=club, member=user)
    club_member_info.delete()
    messages.success(request, _("Done. You have left the club."))
    if not club.members.filter(is_active=True):
        club.delete()
        Notification.objects.filter(club=club).delete()
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
        if self.success:
            return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})
        elif not self.success:
            return reverse_lazy('democracy:kick_members', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['club_id']
        context = add_club_context(self.request, context, club_id)
        return context

    @staticmethod
    def create_notifications(user, club, kicked_members):
        club_members = club.members.filter(is_active=True).exclude(pk=user.id)
        for kicked in kicked_members:
            for member in club_members:
                Notification.objects.create(type=Notification.KICKED,
                                            activator=user,
                                            club=club,
                                            object_member=kicked,
                                            recipient=member)

    def form_valid(self, form):
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        club_admins = club.admin_members.all()
        kicked_members = form.cleaned_data['members']
        if kicked_members:
            for member in kicked_members:
                if member in club_admins:
                    club.admin_members.remove(member)
                club.members.remove(member)
                club_member_info = get_object_or_404(ClubMemberInfo, club=club, member=member)
                club_member_info.delete()
                Notification.objects.filter(club=club, recipient=member).delete()
            club.save()
            self.create_notifications(self.request.user, club, kicked_members)
            if len(kicked_members) == 1:
                messages.success(self.request, _("Member successfully kicked from club."))
            else:
                messages.success(self.request, _("Members successfully kicked from club."))
            self.success = True
        else:
            messages.error(self.request, _("You haven't selected anyone to kick!"))
            self.success = False
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
        if self.success:
            return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})
        elif not self.success:
            return reverse_lazy('democracy:promote_members', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club_id = self.kwargs['club_id']
        context = add_club_context(self.request, context, club_id)
        return context

    @staticmethod
    def create_notifications(user, club, promoted_members):
        club_members = club.members.filter(is_active=True).exclude(pk=user.id)
        for promoted in promoted_members:
            for member in club_members:
                Notification.objects.create(type=Notification.PROMOTED,
                                            activator=user,
                                            club=club,
                                            object_member=promoted,
                                            recipient=member)

    def form_valid(self, form):
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        promoted_members = form.cleaned_data['members']
        if promoted_members:
            for member in promoted_members:
                club.admin_members.add(member)
            club.save()
            self.create_notifications(self.request.user, club, promoted_members)
            if len(promoted_members) == 1:
                messages.success(self.request, _("Member successfully promoted to admin."))
            else:
                messages.success(self.request, _("Members successfully promoted to admin."))
            self.success = True
        else:
            messages.error(self.request, _("You haven't selected anyone to promote!"))
            self.success = False
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
        view_opt = self.kwargs['view_opt'] if 'view_opt' in self.kwargs else 'all'
        order_opt = self.kwargs['order_opt'] if 'order_opt' in self.kwargs else 'title'
        display_opt = self.kwargs['display_opt'] if 'display_opt' in self.kwargs else 'posters'
        context['view_opt'] = view_opt
        context['order_opt'] = order_opt
        context['display_opt'] = display_opt
        if view_opt == 'all':
            context['view_opt_tag'] = _("All")
        elif view_opt == 'not_voted':
            context['view_opt_tag'] = _("Not voted")
        elif view_opt == 'only_voted':
            context['view_opt_tag'] = _("Voted")
        if order_opt == 'title':
            context['order_opt_string'] = "film.filmdb.title"
            context['order_opt_tag'] = _("Title")
        elif order_opt == 'date_proposed':
            context['order_opt_string'] = "film.pub_datetime"
            context['order_opt_tag'] = _("Proposed")
        elif order_opt == 'year':
            context['order_opt_string'] = "film.filmdb.year"
            context['order_opt_tag'] = _("Year")
        elif order_opt == 'duration':
            context['order_opt_string'] = "duration"
            context['order_opt_tag'] = _("Duration")
        elif order_opt == 'user_vote':
            context['order_opt_string'] = "vote_points"
            context['order_opt_tag'] = _("My vote")
        if display_opt == 'posters':
            context['display_opt_tag'] = _("Posters")
        elif display_opt == 'list':
            context['display_opt_tag'] = _("List")
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
                if view_opt == 'all' or view_opt == 'only_voted':
                    user_vote = get_object_or_404(Vote, user=self.request.user, film=film)
                    candidate_films.append({
                        'film': film,
                        'voted': True,
                        'vote_points': - user_vote.vote_score,
                        'duration': film_duration,
                        'vote': user_vote.vote_karma,
                    })
            elif view_opt != 'only_voted':
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
        film = get_object_or_404(Film, pk=self.film_id)
        if self.success:
            return reverse_lazy(
                'democracy:film_detail',
                kwargs={'film_id': film.id,
                        'film_slug': film.filmdb.slug,
                        'view_opt': 'all',
                        'order_opt': 'title',
                        'display_opt': 'posters'}
            )
        else:
            return reverse_lazy(
                'democracy:add_new_film',
                kwargs={'club_id': self.kwargs['club_id']}
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, pk=self.kwargs['club_id'])
        return context

    @staticmethod
    def create_notifications(user, club, film):
        club_members = club.members.filter(is_active=True).exclude(pk=user.id)
        for member in club_members:
            Notification.objects.create(type=Notification.ADDED_FILM,
                                        activator=user,
                                        club=club,
                                        object_film=film,
                                        recipient=member)

    def form_valid(self, form):
        user = self.request.user
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        imdb_key = form.cleaned_data['imdb_input']
        if Film.objects.filter(club=club.id, imdb_id=imdb_key, seen=False):
            messages.error(self.request, _('That film is already in the candidate list!'))
            self.success = False
        else:
            filmdb, created = FilmDb.objects.get_or_create(imdb_id=imdb_key)
            if created or (not created and not filmdb.title):
                self.success = update_filmdb_omdb_info(filmdb)
                if not self.success:
                    messages.error(self.request, _('Sorry, we could not find that film in the database...'))
            else:
                self.success = True
            if self.success:
                film = Film.objects.create(
                    id=random_film_id_generator(club.id),
                    imdb_id=imdb_key,
                    proposed_by=user,
                    club=club,
                    filmdb=filmdb,
                )
                film.save()
                self.create_notifications(user, club, film)
                self.film_id = film.id
                messages.success(self.request, _('New film added! Be the first to vote it!'))
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class RankingParticipantsView(UserPassesTestMixin, generic.TemplateView):

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
class RankingResultsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request, self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'ranking_results'
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        context['club'] = club
        ranking_generator = RankingGenerator(self.request, club.id)
        ranking_results, participants = ranking_generator.generate_ranking()
        context['ranking_results'] = ranking_results
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
        club = get_object_or_404(Club, pk=self.kwargs['club_id'])
        invitation_link, tmp = InvitationLink.objects.get_or_create(club=club, invited_email=form.cleaned_data['email'])
        invitation_link.save()
        messages.success(self.request, _('An invitation email has been sent to: ') + form.cleaned_data['email'])
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
        invited_email = str(urlsafe_base64_decode(self.kwargs['uemailb64']), 'utf-8')
        club = self.get_object(Club, self.kwargs['uclubidb64'])
        if club is not None and user.email == invited_email:
            club_members = club.members.filter(is_active=True)
            invitation_link = InvitationLink.objects.filter(club=club, invited_email=user.email)
            if inviter in club_members and user not in club_members and invitation_link:
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

    @staticmethod
    def create_notifications(user, club):
        club_members = club.members.filter(is_active=True).exclude(pk=user.id)
        for member in club_members:
            Notification.objects.create(type=Notification.JOINED,
                                        activator=user,
                                        club=club,
                                        recipient=member)

    def form_valid(self, form):
        user = self.request.user
        club = self.get_object(Club, self.kwargs['uclubidb64'])
        club_members = club.members.filter(is_active=True)
        if user not in club_members:
            club.members.add(self.request.user)
            club.save()
            club_member_info = ClubMemberInfo.objects.create(club=club, member=user)
            club_member_info.save()
            self.create_notifications(user, club)
            invitation_link = InvitationLink.objects.get(club=club, invited_email=user.email)
            invitation_link.delete()
        messages.success(self.request, _('Congratulations! You have are now a proud member of the club!'))
        return super().form_valid(form)

    def get_success_url(self):
        club = self.get_object(Club, self.kwargs['uclubidb64'])
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': club.id})

