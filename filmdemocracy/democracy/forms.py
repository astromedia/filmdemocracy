from django import forms

from filmdemocracy.democracy.models import Film


class FilmAddNewForm(forms.ModelForm):
    url = forms.CharField(max_length=200, help_text='IMDb url')

    class Meta:
        model = Film
        fields = ['title', 'url']
