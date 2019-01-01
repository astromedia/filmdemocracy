from django import forms
from django.utils import timezone

from filmdemocracy.democracy.models import Film


def process_faff_url(form):
    """Validate that the url is a valid FAff url, and return FAff id."""
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
        raise forms.ValidationError(f"Invalid FilmAffinity url")


class FilmAddNewForm(forms.ModelForm):
    imdb_url = forms.CharField(
        max_length=200,
        help_text='IMDb url',
    )
    faff_url = forms.CharField(
        max_length=200,
        help_text='FilmAffinity url',
        required=False,
    )

    class Meta:
        model = Film
        fields = ['imdb_url', 'faff_url']

    def clean_imdb_url(self):
        """
        Validate that the url is a valid IMDb url,
        that a movie with that IMDb key does not exist,
        and return IMDb id.
        """
        imdb_url = self.cleaned_data['imdb_url']
        try:
            if 'imdb' not in imdb_url:
                raise ValueError
            url_list = imdb_url.split('/')
            title_position = url_list.index('title')
            imdb_key = url_list[title_position + 1]
            if 'tt' not in imdb_key or len(imdb_key) is not 9:
                raise ValueError
            else:
                films_imdb_ids = Film.objects.values_list('imdb_id')
                if imdb_key in films_imdb_ids:
                    raise KeyError
                else:
                    return imdb_key
        except ValueError:
            raise forms.ValidationError(
                f"Invalid IMDb url"
            )
        except KeyError:
            raise forms.ValidationError(
                f"A movie with that IMDb key is already proposed!"
            )

    def clean_faff_url(self):
        if self.cleaned_data['faff_url']:
            faff_key = process_faff_url(self)
            return faff_key
        else:
            return ''


class FilmAddFilmAffForm(forms.ModelForm):
    faff_url = forms.CharField(
        max_length=200,
        help_text='FilmAffinity url',
    )

    class Meta:
        model = Film
        fields = ['faff_url']

    def clean_faff_url(self):
        faff_key = process_faff_url(self)
        return faff_key


class FilmSeenForm(forms.ModelForm):

    class Meta:
        model = Film
        fields = ['seen_date']

    def clean_seen_date(self):
        seen_date = self.cleaned_data['seen_date']
        film = self.instance
        if seen_date < film.pub_date.date():
            raise forms.ValidationError(
                "You can't see films before they are proposed!"
            )
        elif seen_date > timezone.now().date():
            raise forms.ValidationError(
                "You can't see films in the future!"
            )
        else:
            return seen_date
