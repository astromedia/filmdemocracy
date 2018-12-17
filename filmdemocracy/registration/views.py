from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import generic

from filmdemocracy.registration import forms


class SignUpView(generic.CreateView):
    form_class = forms.SignupForm
    success_url = reverse_lazy('registration:login')
    template_name = 'registration/signup.html'


@method_decorator(login_required, name='dispatch')
class DelAccountConfirmView(generic.TemplateView):
    template_name = 'registration/del_account_confirm.html'


def del_account(request):
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
