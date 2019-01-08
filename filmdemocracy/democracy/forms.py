from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.contrib.admin.widgets import AdminDateWidget

from filmdemocracy.democracy.models import Film, FilmDb
from filmdemocracy.registration.models import User


def process_imdb_url(form):
    """
    Validate that the url is a valid IMDb url and return IMDb id.
    """
    imdb_url = form.cleaned_data['imdb_url']
    try:
        if 'imdb' not in imdb_url:
            raise ValueError
        url_list = imdb_url.split('/')
        title_position = url_list.index('title')
        imdb_key = url_list[title_position + 1]
        if 'tt' not in imdb_key or len(imdb_key) is not 9:
            raise ValueError
        else:
            return imdb_key.replace('tt', '')
    except ValueError:
        raise forms.ValidationError(_("Invalid IMDb url."))


def process_faff_url(form):
    """
    Validate that the url is a valid FAff url, and return FAff id.
    """
    try:
        faff_url = form.cleaned_data['faff_url']
        if 'filmaffinity' not in faff_url:
            raise ValueError
        try:
            filmaff_key = faff_url.split('film')[2]
        except IndexError:
            raise ValueError
        if '.html' in filmaff_key:
            filmaff_key = filmaff_key.replace('.html', '')
        if len(filmaff_key) is not 6:
            raise ValueError
        else:
            return filmaff_key
    except ValueError:
        raise forms.ValidationError(_("Invalid FilmAffinity url."))


class FilmAddNewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.club_id = kwargs.pop('club_id', None)
        super(FilmAddNewForm, self).__init__(*args, **kwargs)

    imdb_url = forms.CharField(
        max_length=200,
        help_text=_('IMDb url'),
    )
    faff_url = forms.CharField(
        max_length=200,
        help_text=_('FilmAffinity url'),
        required=False,
    )

    class Meta:
        model = Film
        fields = ['imdb_url', 'faff_url']

    def clean_imdb_url(self):
        imdb_key = process_imdb_url(self)
        film_id = f'{self.club_id}{imdb_key}'
        if Film.objects.filter(pk=film_id):
            raise forms.ValidationError(
                _("That movie is already proposed!")
            )
        else:
            return imdb_key

    def clean_faff_url(self):
        if self.cleaned_data['faff_url']:
            faff_key = process_faff_url(self)
            return faff_key
        else:
            return ''


class FilmAddFilmAffForm(forms.ModelForm):
    faff_url = forms.CharField(
        max_length=200,
        help_text=_('FilmAffinity url'),
    )

    class Meta:
        model = FilmDb
        fields = ['faff_url']

    def clean_faff_url(self):
        faff_key = process_faff_url(self)
        return faff_key


class FilmSeenForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(pk=0),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.film_id = kwargs.pop('film_id', None)
        club_members = kwargs.pop('club_members', None)
        super(FilmSeenForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = club_members
        self.fields['seen_date'].widget = AdminDateWidget()

    class Meta:
        model = Film
        fields = ['seen_date', 'members']

    def clean_seen_date(self):
        seen_date = self.cleaned_data['seen_date']
        if not seen_date:
            raise forms.ValidationError(
                _("You must set a date.")
            )
        film = get_object_or_404(Film, pk=self.film_id)
        if seen_date < film.pub_date.date():
            raise forms.ValidationError(
                _("You can't see films before they are proposed!")
            )
        elif seen_date > timezone.now().date():
            raise forms.ValidationError(
                _("You can't see films in the future!")
            )
        else:
            return seen_date

    def clean_members(self):
        members = self.cleaned_data['members']
        if not members:
            raise forms.ValidationError(
                _("Someone must have seen it... right?")
            )
        else:
            return members
