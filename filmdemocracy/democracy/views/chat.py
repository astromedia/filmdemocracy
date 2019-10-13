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
from filmdemocracy.utils import NotificationsHelper
from filmdemocracy.utils import RankingGenerator


@method_decorator(login_required, name='dispatch')
class ChatClubView(UserPassesTestMixin, generic.TemplateView):

    def test_func(self):
        return user_is_club_member_check(self.request.user, club_id=self.kwargs['club_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'chat'
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        context = add_club_context(context, club)
        posts = ChatClubPost.objects.filter(club=club)
        context['posts'] = posts.order_by('-datetime')[:1000]  # TODO
        return context


@login_required
def post_in_chat_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    if not user_is_club_member_check(request.user, club=club):
        return HttpResponseForbidden()
    post_text = request.POST['text']
    if not post_text.lstrip() == '':
        post = ChatClubPost.objects.create(user_sender=request.user, club=club, text=post_text)
        post.save()
        chat_info, tmp = ChatClubInfo.objects.get_or_404(club=club)
        chat_info.last_post = post
        chat_info.save()
    return HttpResponseRedirect(reverse('democracy:chat_club', kwargs={'club_id': club.id}))


@login_required
def delete_chat_club_post(request, club_id, post_id):
    post = get_object_or_404(ChatClubPost, id=post_id)
    club = get_object_or_404(Club, id=club_id)
    if request.user != post.user:
        if not user_is_club_admin_check(request.user, club=club):
            return HttpResponseForbidden()
    post.deleted = True
    post.save()
    return HttpResponseRedirect(reverse('democracy:chat_club', kwargs={'club_id': club.id}))


@method_decorator(login_required, name='dispatch')
class ChatContactsView(generic.TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_clubs = user.club_set.all()
        unique_contacts = []
        for club in user_clubs:
            for contact in club.members.filter(is_active=True).exclude(id=self.request.user.id):
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
        return users_know_each_other_check(self.request, self.kwargs['chat_user_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'chat'
        chat_user = get_object_or_404(User, id=self.kwargs['chat_user_id'])
        context['chat_user'] = chat_user
        posts_a = ChatUsersPost.objects.filter(user_sender=self.request.user, user_receiver=chat_user)
        posts_b = ChatUsersPost.objects.filter(user_sender=chat_user, user_receiver=self.request.user)
        posts = posts_a | posts_b
        context['posts'] = posts.order_by('-datetime')[:1000]
        return context


@login_required
def post_in_chat_users(request, chat_user_id):
    if not users_know_each_other_check(request, chat_user_id):
        return HttpResponseForbidden()
    chat_user = get_object_or_404(User, id=chat_user_id)
    post_text = request.POST['text']
    if not post_text.lstrip() == '':
        post = ChatUsersPost.objects.create(user_sender=request.user, user_receiver=chat_user, text=post_text)
        post.save()
        for users_tuple in [(request.user, chat_user), (chat_user, request.user)]:
            chat_info, tmp = ChatUsersInfo.objects.get_or_create(user=users_tuple[0], user_known=users_tuple[1])
            chat_info.last_post = post
            chat_info.save()
    return HttpResponseRedirect(reverse('democracy:chat_users', kwargs={'chat_user_id': chat_user_id}))


@login_required
def delete_chat_users_post(request, post_id):
    post = get_object_or_404(ChatUsersPost, id=post_id)
    if request.user != post.user:
        return HttpResponseForbidden()
    post.deleted = True
    post.save()
    return HttpResponseRedirect(reverse('democracy:chat_users', kwargs={'chat_user_id': post.user_receiver.id}))
