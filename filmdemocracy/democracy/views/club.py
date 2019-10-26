import hashlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.html import format_html

from dal import autocomplete

from filmdemocracy.democracy import forms
from filmdemocracy.core.models import Notification
from filmdemocracy.democracy.models import Club, ClubMemberInfo, Invitation, ChatClubInfo, Meeting, FilmDb, Film, Vote, FilmComment
from filmdemocracy.registration.models import User

from filmdemocracy.core.utils import user_is_club_member_check, user_is_club_admin_check
from filmdemocracy.core.utils import add_club_context, update_filmdb_omdb_info, extract_options
from filmdemocracy.core.utils import random_club_id_generator, random_film_public_id_generator
from filmdemocracy.core.utils import RankingGenerator, SpamHelper


@method_decorator(login_required, name='dispatch')
class CreateClubView(generic.FormView):
    form_class = forms.EditClubForm
    new_club = None

    def get_success_url(self):
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
        ClubMemberInfo.objects.create(club=new_club, member=user)
        ChatClubInfo.objects.create(club=new_club)
        messages.success(self.request, _(f"New club created! Now you can invite people to your club, "
                                         f"propose films, and organize meetings."))
        self.new_club = new_club
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class ClubDetailView(UserPassesTestMixin, generic.DetailView):
    model = Club
    pk_url_kwarg = 'club_id'

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'club_detail'
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context = add_club_context(context, club)
        club_meetings = Meeting.objects.filter(club=club, date__gte=timezone.now().date())
        if club_meetings:
            context['next_meetings'] = club_meetings.order_by('date')[0:3]
            context['extra_meetings'] = len(club_meetings) > 3
        last_comments = FilmComment.objects.filter(club=club, deleted=False)
        if last_comments:
            context['last_comments'] = last_comments.order_by('-datetime')[0:5]
        club_films = Film.objects.filter(club=club)
        if club_films:
            films_last_pub = club_films.order_by('-created_datetime')
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
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context = add_club_context(context, club)
        member = get_object_or_404(User, id=self.kwargs['user_id'])
        context['member'] = member
        club_member_info = get_object_or_404(ClubMemberInfo, club=club, member=member)
        context['club_member_info'] = club_member_info
        all_votes = member.vote_set.filter(club=club)
        context['num_of_votes'] = all_votes.count()
        club_films = Film.objects.filter(club=club)
        club_films_not_seen = club_films.filter(seen=False)
        votes = [vote for vote in all_votes if vote.film in club_films_not_seen]
        context['member_votes'] = votes
        member_seen_films = member.seen_by.filter(club=club)
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
        return user_is_club_admin_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})


@method_decorator(login_required, name='dispatch')
class EditClubPanelView(UserPassesTestMixin, generic.UpdateView):
    model = Club
    pk_url_kwarg = 'club_id'
    fields = ['panel']

    def test_func(self):
        return user_is_club_admin_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})


@login_required
def leave_club(request, club_id):
    # TODO: include notifications?
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(request.user, club=club):
        return HttpResponseForbidden()
    context = {}
    context = add_club_context(context, club)
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
    return HttpResponseRedirect(reverse('core:home'))


@login_required
def self_demote(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_admin_check(request.user, club=club):
        return HttpResponseForbidden()
    context = add_club_context({}, club)
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
        return user_is_club_admin_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_form_kwargs(self):
        kwargs = super(KickMembersView, self).get_form_kwargs()
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        club_members = club.members.filter(is_active=True)
        kickable_members = club_members.exclude(id=self.request.user.id)
        kwargs.update({'kickable_members': kickable_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context = add_club_context(context, club)
        return context

    @staticmethod
    def create_notifications(user, club, kicked_members):
        club_members = club.members.filter(is_active=True).exclude(id=user.id)
        for kicked in kicked_members:
            Notification.objects.create(type=Notification.KICKED,
                                        activator=user,
                                        club=club,
                                        object_id=kicked.id,
                                        recipient=kicked)
            for member in club_members:
                Notification.objects.create(type=Notification.KICKED,
                                            activator=user,
                                            club=club,
                                            object_id=kicked.id,
                                            recipient=member)

    def form_valid(self, form):
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        club_admins = club.admin_members.all()
        kicked_members = form.cleaned_data['members']
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
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class PromoteMembersView(UserPassesTestMixin, generic.FormView):
    form_class = forms.PromoteMembersForm

    def test_func(self):
        return user_is_club_admin_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_form_kwargs(self):
        kwargs = super(PromoteMembersView, self).get_form_kwargs()
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        club_members = club.members.filter(is_active=True)
        promotable_members = club_members.exclude(id=self.request.user.id)
        kwargs.update({'promotable_members': promotable_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context = add_club_context(context, club)
        return context

    @staticmethod
    def create_notifications(user, club, promoted_members):
        club_members = club.members.filter(is_active=True).exclude(id=user.id)
        for promoted in promoted_members:
            for member in club_members:
                Notification.objects.create(type=Notification.PROMOTED,
                                            activator=user,
                                            club=club,
                                            object_id=promoted.id,
                                            recipient=member)

    def form_valid(self, form):
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        promoted_members = form.cleaned_data['members']
        for member in promoted_members:
            club.admin_members.add(member)
        club.save()
        self.create_notifications(self.request.user, club, promoted_members)
        if len(promoted_members) == 1:
            messages.success(self.request, _("Member successfully promoted to admin."))
        else:
            messages.success(self.request, _("Members successfully promoted to admin."))
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CandidateFilmsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'candidate_films'
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context['club'] = club
        club_films = Film.objects.filter(club=club, seen=False)
        options_string = self.kwargs['options_string'] if 'options_string' in self.kwargs and self.kwargs['options_string'] else None
        view_option, order_option, display_option = extract_options(options_string)
        context['view_option'] = view_option
        context['order_option'] = order_option
        context['display_option'] = display_option
        if view_option == '&view=not_voted':
            context['view_option_tag'] = _("Not voted")
        elif view_option == '&view=only_voted':
            context['view_option_tag'] = _("Voted")
        else:
            context['view_option_tag'] = _("All")
        if order_option == '&order=date_proposed':
            context['order_option_string'] = "film.created_datetime"
            context['order_option_tag'] = _("Proposed")
        elif order_option == '&order=year':
            context['order_option_string'] = "film.db.year"
            context['order_option_tag'] = _("Year")
        elif order_option == '&order=duration':
            context['order_option_string'] = "duration"
            context['order_option_tag'] = _("Duration")
        elif order_option == '&order=user_vote':
            context['order_option_string'] = "vote_points"
            context['order_option_tag'] = _("My vote")
        else:
            context['order_option_string'] = "film.db.title"
            context['order_option_tag'] = _("Title")
        if display_option == '&display=list':
            context['display_option_tag'] = _("List")
        else:
            context['display_option_tag'] = _("Posters")
        candidate_films = []
        for film in club_films:
            film_voters = [vote.user.username for vote in film.vote_set.all()]
            if self.request.user.username in film_voters:
                if not view_option or view_option == '&view=only_voted':
                    user_vote = get_object_or_404(Vote, user=self.request.user, film=film)
                    candidate_films.append({
                        'film': film,
                        'voted': True,
                        'vote_points': - user_vote.vote_score,
                        'duration': film.db.duration_in_mins_int,
                        'vote': user_vote.vote_karma,
                    })
            elif view_option != '&view=only_voted':
                candidate_films.append({
                    'film': film,
                    'voted': False,
                    'vote_points': -2.5,
                    'duration': film.db.duration_in_mins_int,
                    'vote': False,
                })
        context['candidate_films'] = candidate_films
        return context


@method_decorator(login_required, name='dispatch')
class SeenFilmsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context['club'] = club
        seen_films = Film.objects.filter(club=club, seen=True)
        context['seen_films'] = seen_films
        return context


# @method_decorator(login_required, name='dispatch')
# class AddNewFilmView(UserPassesTestMixin, generic.FormView):
#     form_class = forms.FilmAddNewForm
#     film_added = False
#     new_film_public_id = None
#
#     def test_func(self):
#         return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])
#
#     def get_form_kwargs(self):
#         kwargs = super(AddNewFilmView, self).get_form_kwargs()
#         kwargs.update({'club_id': self.kwargs['club_id']})
#         return kwargs
#
#     def get_success_url(self):
#         club = get_object_or_404(Club, id=self.kwargs['club_id'])
#         if self.film_added:
#             film = get_object_or_404(Film, club=club, public_id=self.new_film_public_id)
#             return reverse('democracy:film_detail', kwargs={'club_id': club.id,
#                                                             'film_public_id': film.public_id,
#                                                             'film_slug': film.db.slug})
#         else:
#             return reverse_lazy('democracy:add_new_film', kwargs={'club_id': club.id})
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         club = get_object_or_404(Club, id=self.kwargs['club_id'])
#         context['club'] = club
#         return context
#
#     @staticmethod
#     def create_notifications(user, club, film):
#         club_members = club.members.filter(is_active=True).exclude(id=user.id)
#         for member in club_members:
#             Notification.objects.create(type=Notification.ADDED_FILM,
#                                         activator=user,
#                                         club=club,
#                                         object_id=film.id,
#                                         recipient=member)
#
#     def form_valid(self, form):
#         user = self.request.user
#         club = get_object_or_404(Club, id=self.kwargs['club_id'])
#         imdb_key = form.cleaned_data['imdb_input']
#         if Film.objects.filter(club=club, imdb_id=imdb_key, seen=False):
#             messages.error(self.request, _('That film is already in the candidate list!'))
#             self.film_added = False
#         else:
#             filmdb, created = FilmDb.objects.get_or_create(imdb_id=imdb_key)
#             if created or (not created and not filmdb.title):
#                 self.film_added = update_filmdb_omdb_info(filmdb)
#                 if not self.film_added:
#                     messages.error(self.request, _('Sorry, we could not find that film in the database...'))
#             else:
#                 self.film_added = True
#             if self.film_added:
#                 film = Film.objects.create(
#                     public_id=random_film_public_id_generator(club),
#                     imdb_id=imdb_key,
#                     proposed_by=user,
#                     club=club,
#                     db=filmdb,
#                 )
#                 self.create_notifications(user, club, film)
#                 self.new_film_public_id = film.public_id
#                 messages.success(self.request, _('New film added! Be the first to vote it!'))
#         return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class AddNewFilmView(UserPassesTestMixin, generic.FormView):
    form_class = forms.FilmAddNewForm
    films_added_counter = 0
    new_film_public_id = None

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_success_url(self):
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        if self.films_added_counter == 1:
            film = get_object_or_404(Film, club=club, public_id=self.new_film_public_id)
            return reverse('democracy:film_detail', kwargs={'club_id': club.id,
                                                            'film_public_id': film.public_id,
                                                            'film_slug': film.db.slug})
        elif self.films_added_counter > 1:
            return reverse('democracy:candidate_films', kwargs={'club_id': club.id})
        else:
            return reverse_lazy('democracy:add_new_film', kwargs={'club_id': club.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context['club'] = club
        return context

    @staticmethod
    def create_notifications(user, club, film):
        club_members = club.members.filter(is_active=True).exclude(id=user.id)
        for member in club_members:
            Notification.objects.create(type=Notification.ADDED_FILM,
                                        activator=user,
                                        club=club,
                                        object_id=film.id,
                                        recipient=member)

    def form_valid(self, form):
        user = self.request.user
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        filmdbs = form.cleaned_data['filmdbs']

        for filmdb in filmdbs:
            film = Film.objects.filter(club=club, db=filmdb, seen=False)
            if film:
                message_warning = '%s %s' % (_('This film is already in the candidate list:'), f'{film[0].db.title}')
                messages.warning(self.request, message_warning)
                return super().form_valid(form)

        for filmdb in filmdbs:
            film = Film.objects.create(
                public_id=random_film_public_id_generator(club),
                proposed_by=user,
                club=club,
                db=filmdb,
            )
            self.films_added_counter += 1
            self.create_notifications(user, club, film)
            self.new_film_public_id = film.public_id

        if self.films_added_counter >= 1:
            if self.films_added_counter == 1:
                messages.success(self.request, _('New film added! Be the first to vote it!'))
            elif self.films_added_counter > 1:
                messages.success(self.request, _('New films added!'))

        return super().form_valid(form)


class NewFilmAutocompleteView(autocomplete.Select2QuerySetView):

    def get_result_label(self, item):
        return format_html(
            '<p class="m-0 p-0" style="line-height: 16px"><span class="font-weight-bold">{}</span> <span class="text-muted">({})</span></p>'
            '<p class="m-0 p-0" style="line-height: 13px"><span class="text-muted font-italic"><small>{}</small></span></p>',
            item.title,
            item.year,
            item.director,
        )

    def get_selected_result_label(self, item):
        return item.title

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return FilmDb.objects.none()
        qs = FilmDb.objects.all()
        if self.q:
            qs = qs.filter(title__istartswith=self.q)
        return qs


@method_decorator(login_required, name='dispatch')
class RankingParticipantsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'film_ranking'
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context = add_club_context(context, club)
        return context


@method_decorator(login_required, name='dispatch')
class RankingResultsView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'ranking_results'
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context['club'] = club
        ranking_generator = RankingGenerator(self.request, club.id)
        ranking_results, participants = ranking_generator.generate_ranking()
        context['ranking_results'] = ranking_results
        context['participants'] = participants
        return context


@method_decorator(login_required, name='dispatch')
class InviteNewMemberView(UserPassesTestMixin, generic.FormView):
    form_class = forms.InviteNewMemberForm
    subject_template = 'democracy/emails/invite_new_member_subject.txt'
    email_template = 'democracy/emails/invite_new_member_email.html'
    html_email_template = 'democracy/emails/invite_new_member_email_html.html'

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(InviteNewMemberView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        return kwargs

    @staticmethod
    def create_notifications(user, club, email, invitation):
        try:
            invited_user = User.objects.get(email=email)
            Notification.objects.create(type=Notification.INVITED,
                                        activator=user,
                                        object_id=invitation.id,
                                        club=club,
                                        recipient=invited_user)
        except User.DoesNotExist:
            pass

    def form_valid(self, form):
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        email = form.cleaned_data["email"]
        invitation_text = form.cleaned_data["invitation_text"]
        hash_invited_email = hashlib.sha256(email.encode('utf-8')).hexdigest()
        invitation = Invitation.objects.create(club=club,
                                               inviter=self.request.user,
                                               hash_invited_email=hash_invited_email,
                                               invitation_text=invitation_text)
        self.create_notifications(self.request.user, club, email, invitation)
        email_context = {'invitation': invitation}
        to_emails_list = [email]
        spam_helper = SpamHelper(self.request, self.subject_template, self.email_template, self.html_email_template)
        spam_helper.send_emails(to_emails_list, email_context)
        messages.success(self.request, _('An invitation email has been sent to: ') + form.cleaned_data['email'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context['club'] = club
        return context


@method_decorator(login_required, name='dispatch')
class InviteNewMemberConfirmView(generic.FormView):
    form_class = forms.InviteNewMemberConfirmForm
    invitation = None
    valid_link = False

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        self.invitation = get_object_or_404(Invitation, id=self.kwargs['invitation_id'])
        if self.invitation and self.invitation.is_active:
            user = self.request.user
            hash_user_email = hashlib.sha256(user.email.encode('utf-8')).hexdigest()
            inviter = self.invitation.inviter
            club = self.invitation.club
            if club is not None and hash_user_email == self.invitation.hash_invited_email:
                club_members = club.members.filter(is_active=True)
                if inviter in club_members and user not in club_members:
                    self.valid_link = True
                    return super().dispatch(*args, **kwargs)
        # Display the "invitation link not valid" error page.
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.valid_link:
            club = self.invitation.club
            context['club'] = club
            context['valid_link'] = True
        else:
            context.update({'form': None, 'valid_link': False})
        return context

    @staticmethod
    def create_notifications(user, club):
        club_members = club.members.filter(is_active=True)
        for member in club_members:
            Notification.objects.create(type=Notification.JOINED,
                                        activator=user,
                                        club=club,
                                        object_id=user.id,
                                        recipient=member)

    def form_valid(self, form):
        user = self.request.user
        club = self.invitation.club
        # Avoid user accepting invitation link twice
        if self.invitation.is_active:
            club.members.add(self.request.user)
            club.save()
            ClubMemberInfo.objects.create(club=club, member=user)
            self.create_notifications(user, club)
            # Deactivate all other invitations the user may have received before
            pending_invitations = Invitation.objects.filter(club=club, hash_invited_email=self.invitation.hash_invited_email)
            for pending_invitation in pending_invitations:
                pending_invitation.is_active = False
                pending_invitation.save()
        messages.success(self.request, _('Congratulations! You have are now a proud member of the club!'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.invitation.club.id})
