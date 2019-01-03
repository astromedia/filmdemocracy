from django.views import generic

from filmdemocracy.socialclub.models import Club


class HomeView(generic.TemplateView):
    model = Club
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['user_clubs'] = self.request.user.club_set.all()
        return context
