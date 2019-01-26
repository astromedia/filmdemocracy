from django.views import generic
from django.shortcuts import redirect


def redirect_to_home(request):
    return redirect('home')


class HomeView(generic.TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['user_clubs'] = self.request.user.club_set.all()
        return context


class TermsAndConditionsView(generic.TemplateView):
    pass
