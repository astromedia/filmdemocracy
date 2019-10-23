from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic

from filmdemocracy.registration import forms
from filmdemocracy.core.models import Notification


class SignUpView(generic.CreateView):
    form_class = forms.SignupForm
    success_url = reverse_lazy('registration:user_login')

    def form_valid(self, form):
        messages.success(self.request, _("Account created successfully.\nWelcome to FilmDemocracy!"
                                         "\nNow login with your new credentials to continue."))
        return super().form_valid(form)


@login_required
def account_delete(request):

    def create_notifications(_user, _club):
        abandoned_members = _club.members.filter(is_active=True).exclude(id=_user.id)
        for abandoned_member in abandoned_members:
            Notification.objects.create(type=Notification.ABANDONED,
                                        activator=None,
                                        club=_club,
                                        recipient=abandoned_member)

    user = request.user
    user_clubs = user.club_set.all()
    for club in user_clubs:
        club_members = club.members.filter(is_active=True)
        club_admins = club.admin_members.filter(is_active=True)
        if len(club_members) == 1:
            club.delete()
        elif user in club_admins and len(club_admins) == 1 and len(club_members) > 1:
            for member in club_members:
                club.admin_members.add(member)
            club.save()
            create_notifications(user, club)
    user.delete()
    messages.success(request, _("Account deleted successfully."))
    return HttpResponseRedirect(reverse('core:home'))


@method_decorator(login_required, name='dispatch')
class AccountInfoView(generic.TemplateView):
    context_object_name = 'user'

    def get_queryset(self):
        return self.request.user


@method_decorator(login_required, name='dispatch')
class AccountInfoEditView(generic.UpdateView):
    form_class = forms.AccountInfoEditForm
    success_url = reverse_lazy('registration:account_info')

    def get_object(self, queryset=None):
        return self.request.user
