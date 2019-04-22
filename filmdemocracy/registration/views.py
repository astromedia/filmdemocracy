from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic


from filmdemocracy.registration import forms


class SignUpView(generic.CreateView):
    form_class = forms.SignupForm
    success_url = reverse_lazy('registration:user_login')


@login_required
def account_delete(request):
    user = request.user
    user.is_active = False
    user.save()
    messages.success(request, _("Account deleted successfully."))
    return HttpResponseRedirect(reverse('home'))


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
