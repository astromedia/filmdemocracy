from django import forms
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from filmdemocracy.democracy.models import Film, FilmDb, Club, Meeting
from filmdemocracy.registration.models import User


class EditClubForm(forms.ModelForm):
    short_description = forms.CharField(
        max_length=100,
        widget=forms.Textarea,
        label=_('Short description (optional)'),
        required=False,
    )

    class Meta:
        model = Club
        fields = ['name', 'logo', 'short_description']

    def clean_logo(self):
        # TODO: club logo validation
        logo = self.cleaned_data['logo']
        return logo


class KickMembersForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(pk=0),
        required=False
    )

    class Meta:
        model = Club
        fields = ['members']

    def __init__(self, *args, **kwargs):
        kickable_members = kwargs.pop('kickable_members', None)
        super(KickMembersForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = kickable_members


class PromoteMembersForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(pk=0),
        required=False
    )

    class Meta:
        model = Club
        fields = ['members']

    def __init__(self, *args, **kwargs):
        promotable_members = kwargs.pop('promotable_members', None)
        super(PromoteMembersForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = promotable_members


def process_imdb_input(form):
    """ Validate that the input is a valid IMDb film url or key and return IMDb id. """
    # TODO: do this using regexps?

    imdb_input = form.cleaned_data['imdb_input']
    try:
        if 'imdb' in imdb_input:
            url_list = imdb_input.split('/')
            title_position = url_list.index('title')
            imdb_key = url_list[title_position + 1]
            imdb_key = imdb_key.replace('tt', '')
        elif 'imdb' not in imdb_input and 'tt' in imdb_input and len(imdb_input) is 9:
            imdb_key = imdb_input.replace('tt', '')
        elif 'imdb' not in imdb_input and 'tt' not in imdb_input and len(imdb_input) is 7:
            imdb_key = imdb_input
        else:
            raise ValueError
        return imdb_key
    except ValueError:
        raise forms.ValidationError(_("The IMDb film url or key does not seem to be valid."))


# def process_faff_url(form):
#     """
#     Validate that the url is a valid FAff url, and return FAff id.
#     """
#     try:
#         faff_url = form.cleaned_data['faff_url']
#         if 'filmaffinity' not in faff_url:
#             raise ValueError
#         elif 'm.filmaffinity' in faff_url:
#             try:
#                 filmaff_key = faff_url.split('id=')[1][0:6]
#             except IndexError:
#                 raise ValueError
#         else:
#             try:
#                 filmaff_key = faff_url.split('film')[2][0:6]
#             except IndexError:
#                 raise ValueError
#             if '.html' in filmaff_key:
#                 filmaff_key = filmaff_key.replace('.html', '')
#         if len(filmaff_key) is not 6:
#             raise ValueError
#         else:
#             return filmaff_key
#     except ValueError:
#         raise forms.ValidationError(_("Invalid FilmAffinity url."))


class FilmAddNewForm(forms.ModelForm):
    imdb_input = forms.CharField(max_length=200, label=_('IMDb film url or key'),)

    class Meta:
        model = Film
        fields = ['imdb_input']

    def __init__(self, *args, **kwargs):
        self.club_id = kwargs.pop('club_id', None)
        super(FilmAddNewForm, self).__init__(*args, **kwargs)

    def clean_imdb_input(self):
        return process_imdb_input(self)


# class FilmAddFilmAffForm(forms.ModelForm):
#     faff_url = forms.CharField(
#         max_length=200,
#         label=_('FilmAffinity url'),
#     )
#
#     class Meta:
#         model = FilmDb
#         fields = ['faff_url']
#
#     def clean_faff_url(self):
#         faff_key = process_faff_url(self)
#         return faff_key


class FilmSeenForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(pk=0),
        required=False,
    )

    class Meta:
        model = Film
        fields = ['seen_date', 'members']

    def __init__(self, *args, **kwargs):
        self.film_public_id = kwargs.pop('film_public_id', None)
        self.club = get_object_or_404(Club, pk=kwargs.pop('club_id', None))
        club_members = self.club.members.filter(is_active=True)
        super(FilmSeenForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = club_members

    def clean_seen_date(self):
        seen_date = self.cleaned_data['seen_date']
        if not seen_date:
            raise forms.ValidationError(_("You must set a date."))
        film = get_object_or_404(Film, club=self.club, public_id=self.film_public_id)
        if seen_date < film.created_datetime.date():
            raise forms.ValidationError(_("You can't see films before they were proposed!"))
        elif seen_date > timezone.now().date():
            raise forms.ValidationError(_("Time travelling to the future is not possible (yet)."))
        else:
            return seen_date

    def clean_members(self):
        members = self.cleaned_data['members']
        if not members:
            raise forms.ValidationError(_("Someone must have seen it... right?"))
        else:
            return members


class InviteNewMemberForm(forms.Form):
    email = forms.EmailField(label=_("Email"), max_length=254)
    invitation_text = forms.CharField(
        max_length=500,
        widget=forms.Textarea,
        label=_('Send message with email (optional)'),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.club_id = kwargs.pop('club_id', None)
        super(InviteNewMemberForm, self).__init__(*args, **kwargs)


class InviteNewMemberConfirmForm(forms.Form):
    pass


class MeetingsForm(forms.ModelForm):
    description = forms.CharField(
        max_length=300,
        widget=forms.Textarea,
        label=_('Description (optional)'),
        required=False,
    )
    send_spam = forms.BooleanField(label='send_spam', required=False)
    spam_options = forms.ChoiceField(
        choices=(('all', ""), ('interested', ""), ('noone', "")),
        label='spam_options',
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.club_id = kwargs.pop('club_id', None)
        if 'meeting_id' in kwargs:
            self.meeting_id = kwargs.pop('meeting_id', None)
        super(MeetingsForm, self).__init__(*args, **kwargs)
        try:
            meeting = get_object_or_404(Meeting, pk=self.meeting_id)
            self.initial['name'] = meeting.name
            self.initial['description'] = meeting.description
            self.initial['place'] = meeting.place
            self.initial['date'] = meeting.created_datetime
            self.initial['time_start'] = meeting.time_start
        except AttributeError:
            pass

    class Meta:
        model = Meeting
        fields = ['name', 'description', 'place', 'date', 'time_start', 'send_spam', 'spam_options']

    def clean_date(self):
        date = self.cleaned_data['date']
        if date < timezone.now().date():
            raise forms.ValidationError(_("No much sense on planning now a meeting on the past, sorry."))
        return date

    def clean_time_start(self):
        time_start = self.cleaned_data['time_start']
        if time_start:
            date = self.cleaned_data['date']
            if date == timezone.now().date():
                time_start = self.cleaned_data['time_start']
                if time_start < timezone.now().time():
                    raise forms.ValidationError(_("Meetings can't start before they are proposed, sorry."))
        return self.cleaned_data['time_start']
