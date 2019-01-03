import random

from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import generic

from filmdemocracy.socialclub.models import Club
from filmdemocracy.socialclub import forms


@method_decorator(login_required, name='dispatch')
class CreateClubView(generic.FormView):
    form_class = forms.CreateClubForm
    template_name = 'socialclub/create_club.html'

    def get_success_url(self):
        return reverse('home')

    @staticmethod
    def random_id_generator():
        """
        Random id generator, that picks an integer in the [1, 999999] range
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
        new_id = self.random_id_generator()
        new_group = Club.objects.create(
            id=new_id,
            name=form.cleaned_data['name'],
            short_description=form.cleaned_data['short_description'],
            image=form.cleaned_data['image'],
            admin_user=self.request.user,
        )
        new_group.users.add(self.request.user)
        new_group.save()
        return super().form_valid(form)
