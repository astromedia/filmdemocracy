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
from filmdemocracy.democracy.models import Club, Notification, ClubMemberInfo, Invitation
from filmdemocracy.democracy.models import ChatClubPost, ChatUsersPost, ChatUsersInfo, ChatClubInfo, Meeting
from filmdemocracy.democracy.models import FilmDb, Film, Vote, FilmComment
from filmdemocracy.registration.models import User

from filmdemocracy.utils import user_is_club_member_check, user_is_club_admin_check, user_is_organizer_check, users_know_each_other_check
from filmdemocracy.utils import add_club_context, update_filmdb_omdb_info
from filmdemocracy.utils import random_club_id_generator, random_film_public_id_generator
from filmdemocracy.utils import NotificationsHelper, SpamHelper
from filmdemocracy.utils import RankingGenerator


@method_decorator(login_required, name='dispatch')
class MeetingsNewView(UserPassesTestMixin, generic.FormView):
    form_class = forms.MeetingsForm
    subject_template_name = 'democracy/emails/meetings_new_subject.txt'
    email_template_name = 'democracy/emails/meetings_new_email.html'
    html_email_template_name = 'democracy/emails/meetings_new_email_html.html'
    extra_email_context = None
    from_email = 'filmdemocracyweb@gmail.com'

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_form_kwargs(self):
        kwargs = super(MeetingsNewView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context['club'] = club
        context['new_meeting'] = True
        return context

    @staticmethod
    def create_notifications(_user, _club, _meeting):
        club_members = _club.members.filter(is_active=True).exclude(id=_user.id)
        for member in club_members:
            Notification.objects.create(type=Notification.ORGAN_MEET,
                                        activator=_user,
                                        club=_club,
                                        object_meeting=_meeting,
                                        recipient=member)

    def form_valid(self, form):
        user = self.request.user
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        new_meeting = Meeting.objects.create(
            club=club,
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description'],
            organizer=user,
            place=form.cleaned_data['place'],
            date=form.cleaned_data['date'],
            time_start=form.cleaned_data['time_start'],
        )
        new_meeting.save()
        self.create_notifications(user, club, new_meeting)
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
            messages.success(self.request, _('Meeting planned! A notification email has been sent to club members.'))
        else:
            messages.success(self.request, _('Meeting planned!'))
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class MeetingsEditView(UserPassesTestMixin, generic.FormView):
    form_class = forms.MeetingsForm
    subject_template = 'democracy/emails/meetings_edit_subject.txt'
    email_template = 'democracy/emails/meetings_edit_email.html'
    html_email_template = 'democracy/emails/meetings_edit_email_html.html'

    def test_func(self):
        return user_is_organizer_check(self.request.user, self.kwargs['club_id'], self.kwargs['meeting_id'])

    def get_form_kwargs(self):
        kwargs = super(MeetingsEditView, self).get_form_kwargs()
        kwargs.update({'club_id': self.kwargs['club_id']})
        kwargs.update({'meeting_id': self.kwargs['meeting_id']})
        return kwargs

    def get_success_url(self):
        return reverse_lazy('democracy:club_detail', kwargs={'club_id': self.kwargs['club_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['club'] = get_object_or_404(Club, id=self.kwargs['club_id'])
        context['meeting'] = get_object_or_404(Meeting, id=self.kwargs['meeting_id'])
        context['new_meeting'] = False
        return context

    def form_valid(self, form):
        meeting = get_object_or_404(Meeting, id=self.kwargs['meeting_id'])
        meeting.name = form.cleaned_data['name']
        meeting.description = form.cleaned_data['description']
        meeting.place = form.cleaned_data['place']
        meeting.date = form.cleaned_data['date']
        meeting.time_start = form.cleaned_data['time_start']
        meeting.save()
        spam_option = form.cleaned_data['spam_options']
        if spam_option == 'all' or spam_option == 'interested':
            club = get_object_or_404(Club, id=self.kwargs['club_id'])
            spam_helper = SpamHelper(self.request, self.subject_template, self.email_template, self.html_email_template)
            email_context = {
                'organizer': self.request.user,
                'club': club,
                'name': meeting.name,
                'description': meeting.description,
                'place': meeting.place,
                'date': meeting.date,
                'time_start': meeting.time_start,
            }
            if spam_option == 'all':
                spammable_members = club.members.filter(is_active=True)
                to_emails_list = [member.email for member in spammable_members]
                spam_helper.send_emails(to_emails_list, email_context)
                messages.success(self.request, _('Meeting edited! A notification email has been sent to club members.'))
            else:
                spammable_members = meeting.members_yes.all() + meeting.members_maybe.all() + meeting.members_no.all()
                to_emails_list = [member.email for member in spammable_members]
                spam_helper.send_emails(to_emails_list, email_context)
                messages.success(self.request, _('Meeting edited! A notification email has been sent to members interested in it.'))
        else:
            messages.success(self.request, _('Meeting edited!'))
        return super().form_valid(form)


@login_required
def meeting_assistance(request, club_id, meeting_id):
    user = request.user
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(user, club=club):
        return HttpResponseForbidden()
    meeting = get_object_or_404(Meeting, id=meeting_id)
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
    return HttpResponseRedirect(reverse('democracy:club_detail', kwargs={'club_id': club_id}))


@login_required
def delete_meeting(request, club_id, meeting_id):
    organizer_check = user_is_organizer_check(request.user, club_id, meeting_id)
    club = get_object_or_404(Club, id=club_id)
    admin_check = user_is_club_admin_check(request.user, club=club)
    if not organizer_check and not admin_check:
        return HttpResponseForbidden()
    meeting = get_object_or_404(Meeting, id=meeting_id)
    meeting.delete()
    return HttpResponseRedirect(reverse('democracy:club_detail', kwargs={'club_id': club.id}))


@method_decorator(login_required, name='dispatch')
class MeetingsListView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context = add_club_context(context, club)
        club_meetings = Meeting.objects.filter(club=club, date__gte=timezone.now().date())
        context['club_meetings'] = club_meetings.order_by('date')
        return context