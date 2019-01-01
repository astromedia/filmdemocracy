import random

from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import generic

from filmdemocracy.registration.models import User, Club
from filmdemocracy.registration import forms


class SignUpView(generic.CreateView):
    form_class = forms.SignupForm
    success_url = reverse_lazy('registration:user_login')
    template_name = 'registration/user_signup.html'


def account_del(request):
    user = request.user
    user.is_active = False
    user.save()
    # TODO: messages.success(request, 'Usuario desactivado con éxito.')
    return HttpResponseRedirect(reverse('home'))


@method_decorator(login_required, name='dispatch')
class AccountInfoView(generic.TemplateView):
    template_name = 'registration/account_info.html'
    context_object_name = 'user'

    def get_queryset(self):
        return self.request.user


@method_decorator(login_required, name='dispatch')
class AccountInfoEditView(generic.UpdateView):
    form_class = forms.AccountInfoEditForm
    template_name = 'registration/account_info_edit.html'
    success_url = reverse_lazy('registration:account_info')

    def get_object(self, queryset=None):
        return self.request.user


@method_decorator(login_required, name='dispatch')
class CreateClubView(generic.FormView):
    form_class = forms.CreateClubForm
    template_name = 'registration/create_club.html'

    def get_success_url(self):
        return reverse('home')

    @staticmethod
    def random_id_generator():
        """
        Random id generator, that picks an integer in the [1, 999999] range
        among the free ones (i.e., not found in the DB).
        return: new_id: new id number not existing in the database
        """
        if len(Club.objects.all()) == 999999:
            raise Exception('All possible id numbers are picked!')
        else:
            club_ids = Club.objects.values_list('id')
            free_ids = [i for i in range(1, 999999) if i not in club_ids]
            new_id = random.choice(free_ids)
        return new_id

    def form_valid(self, form):
        new_id = self.random_id_generator()
        new_group = Club.objects.create(
            id=new_id,
            name=form.cleaned_data['name'],
            description=form.cleaned_data['description'],
            image=form.cleaned_data['image'],
            admin_user=self.request.user,
        )
        new_group.users.add(self.request.user)
        new_group.save()
        return super().form_valid(form)
