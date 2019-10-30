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

    def form_valid(self, form):
        new_user = form.save()
        messages.success(self.request, _("Account created successfully. Welcome to FilmDemocracy!"))
        self.create_notifications(new_user)
        login(self.request, new_user, backend='django.contrib.auth.backends.ModelBackend')
        return HttpResponseRedirect(reverse_lazy('core:home'))

    @staticmethod
    def create_notifications(user):
        Notification.objects.create(type=Notification.SIGNUP,
                                    activator=user,
                                    club=None,
                                    recipient=user)


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
class AccountInfoView(generic.UpdateView):
    form_class = forms.AccountInfoForm
    success_url = reverse_lazy('core:home')

    def get_object(self, queryset=None):
        return self.request.user
