import random

from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import generic
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

from filmdemocracy.socialclub.models import Club
from filmdemocracy.registration.models import User
from filmdemocracy.democracy.models import Film, Vote
from filmdemocracy.socialclub import forms


def get_club_context(view_request, club_id, context):
    club = get_object_or_404(Club, pk=club_id)
    context['club'] = club
    club_users = club.users.filter(
        is_superuser=False,
        is_active=True,
    )
    club_admins = club.admin_users.all()
    context['club_admins'] = club_admins
    club_members = []
    for member in club_users:
        club_members.append({
            'member': member,
            'is_admin': member in club_admins,
        })
    context['club_members'] = club_members
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
        new_club = Club.objects.create(
            id=self.random_id_generator(),
            name=form.cleaned_data['name'],
            short_description=form.cleaned_data['short_description'],
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
        context = get_club_context(self.request, self.kwargs['pk'], context)
        return context


@method_decorator(login_required, name='dispatch')
class ClubMemberDetailView(generic.DetailView):
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_club_context(
            self.request,
            self.kwargs['club_id'],
            context
        )
        club = context['club']
        member = get_object_or_404(User, pk=self.kwargs['pk'])
        context['member'] = member
        films = Film.objects.all().filter(club_id=club.id, seen=False)
        club_votes = member.vote_set.filter(club_id=club.id)
        context['num_of_votes'] = club_votes.count()
        member_votes = [vote for vote in club_votes if vote.film in films]
        context['member_votes'] = member_votes
        member_films = member.seen_by.filter(club_id=club.id)
        context['member_films'] = member_films
        context['num_of_films_seen'] = member_films.count()
        return context


@method_decorator(login_required, name='dispatch')
class EditClubInfoView(generic.UpdateView):
    model = Club
    fields = ['name', 'logo', 'short_description']

    def get_success_url(self):
        return reverse_lazy(
            'socialclub:club_detail',
            kwargs={'pk': self.kwargs['pk']}
        )


@method_decorator(login_required, name='dispatch')
class EditClubPanelView(generic.UpdateView):
    model = Club
    fields = ['club_panel']

    def get_success_url(self):
        return reverse_lazy(
            'socialclub:club_detail',
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
            context['error_msg'] = _("You must promote other club member "
                                     "to admin before leaving the club.")
            return render(request, 'socialclub/club_detail.html', context)
        else:
            club.admin_users.remove(user)
    club.users.remove(user)
    club.save()
    # TODO: 'You have successfully left the club.'
    return HttpResponseRedirect(reverse('home'))


def selfdemote(request, club_id):
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
            return render(request, 'socialclub/club_detail.html', context)
        else:
            club.admin_users.remove(user)
    club.save()
    # TODO: 'You have successfully demoted yourself.'
    return HttpResponseRedirect(reverse_lazy(
            'socialclub:club_detail',
            kwargs={'pk': club_id}
        ))


@method_decorator(login_required, name='dispatch')
class KickMembersView(generic.FormView):
    form_class = forms.KickMembersForm

    def get_form_kwargs(self):
        kwargs = super(KickMembersView, self).get_form_kwargs()
        club = get_object_or_404(Club, pk=self.kwargs['pk'])
        club_users = club.users.filter(
            is_superuser=False,
            is_active=True,
        )
        club_members = club_users.exclude(pk=self.request.user.id)
        kwargs.update({'club_members': club_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'socialclub:club_detail',
            kwargs={'pk': self.kwargs['pk']}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = get_club_context(self.request, self.kwargs['pk'], context)
        return context

    def form_valid(self, form):
        club = get_object_or_404(Club, pk=self.kwargs['pk'])
        club_admins = club.admin_users.all()
        kicked_members = form.cleaned_data['members']
        for member in kicked_members:
            if member in club_admins:
                club.admin_users.remove(member)
            club.users.remove(member)
        club.save()
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class PromoteMembersToAdminView(generic.FormView):
    form_class = forms.PromoteMembersToAdminForm

    def get_form_kwargs(self):
        kwargs = super(PromoteMembersToAdminView, self).get_form_kwargs()
        club = get_object_or_404(Club, pk=self.kwargs['pk'])
        club_users = club.users.filter(
            is_superuser=False,
            is_active=True,
        )
        club_members = club_users.exclude(pk=self.request.user.id)
        kwargs.update({'club_members': club_members})
        return kwargs

    def get_success_url(self):
        return reverse_lazy(
            'socialclub:club_detail',
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
            club.admin_users.add(member)
        club.save()
        return super().form_valid(form)
