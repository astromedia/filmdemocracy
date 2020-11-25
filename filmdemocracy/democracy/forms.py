from io import BytesIO
import time
import datetime

from django import forms
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile
from dal import autocomplete
from PIL import Image

from filmdemocracy.democracy.models import Film, FilmDb, Club, Meeting
from filmdemocracy.registration.models import User


class EditClubForm(forms.ModelForm):

    # TODO: logo_image validation

    updateImage = forms.BooleanField(widget=forms.HiddenInput(), required=False)
    x = forms.FloatField(widget=forms.HiddenInput(), required=False)
    y = forms.FloatField(widget=forms.HiddenInput(), required=False)
    width = forms.FloatField(widget=forms.HiddenInput(), required=False)
    height = forms.FloatField(widget=forms.HiddenInput(), required=False)
    short_description = forms.CharField(
        max_length=100,
        widget=forms.Textarea,
        label=_('Short description (optional)'),
        required=False,
    )

    class Meta:
        model = Club
        fields = ['updateImage', 'x', 'y', 'width', 'height', 'logo_image', 'name', 'short_description']
        widgets = {
            'logo_image': forms.FileInput(attrs={
                'accept': 'image/*'  # this is not an actual validation! don't rely on that!
            })
        }

    def clean_logo_image(self):

        # TODO: club logo_image validation
        
        update_image = self.cleaned_data.get('updateImage')
        original_image = self.cleaned_data['logo_image']
        x = self.cleaned_data.get('x')
        y = self.cleaned_data.get('y')
        w = self.cleaned_data.get('width')
        h = self.cleaned_data.get('height')
        if update_image and x is not None and y is not None and w is not None and h is not None:
            image = Image.open(original_image)
            cropped_image = image.crop((x, y, w + x, h + y))
            ratio = w / h
            resized_image = cropped_image.resize((int(516 * ratio), 516), Image.ANTIALIAS)
            buffer = BytesIO()
            resized_image.save(fp=buffer, format='JPEG')
            pil_image = ContentFile(buffer.getvalue())
            new_file_name = str(int(time.time())) + '.jpg'
            logo_image = InMemoryUploadedFile(
                pil_image,  # file
                u"logo_image",  # field_name
                new_file_name,  # file name
                'image/jpeg',  # content_type
                pil_image.size,  # size
                None  # content_type_extra
            )
            return logo_image
        else:
            return

    def save(self):
        club = super(EditClubForm, self).save()
        return club


class KickMembersForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(id=0),
        required=False
    )

    class Meta:
        model = Club
        fields = ['members']

    def __init__(self, *args, **kwargs):
        kickable_members = kwargs.pop('kickable_members', None)
        super(KickMembersForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = kickable_members

    def clean_members(self):
        kicked_members = self.cleaned_data['members']
        if not kicked_members:
            raise forms.ValidationError(_("You haven't selected anyone to kick!"))
        return kicked_members


class PromoteMembersForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(id=0),
        required=False
    )

    class Meta:
        model = Club
        fields = ['members']

    def __init__(self, *args, **kwargs):
        promotable_members = kwargs.pop('promotable_members', None)
        super(PromoteMembersForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = promotable_members

    def clean_members(self):
        promoted_members = self.cleaned_data['members']
        if not promoted_members:
            raise forms.ValidationError(_("You haven't selected anyone to promote!"))
        return promoted_members


class ConfirmForm(forms.Form):
    pass


def process_imdb_input(form):
    """ Validate that the input is a valid IMDb film url or key and return IMDb id. """
    # TODO: do this using regexps?


class FilmAddNewForm(forms.Form):
    # https://select2.org/
    filmdbs = forms.ModelMultipleChoiceField(
        queryset=FilmDb.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(
            url='democracy:new_film_autocomplete',
            attrs={
                'data-placeholder': _('Type here the name of the film'),
                'data-minimum-input-length': 3,
                'data-html': True,
            }
        )
    )


class FilmSeenForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(id=0),
        required=False,
    )

    class Meta:
        model = Film
        fields = ['seen_date', 'members']

    def __init__(self, *args, **kwargs):
        self.film_public_id = kwargs.pop('film_public_id', None)
        self.club = get_object_or_404(Club, id=kwargs.pop('club_id', None))
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
    response_choice = forms.ChoiceField(
        choices=(('accept', ""), ('decline', "")),
        label='response_choices',
        required=False
    )


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
    date = forms.DateField(initial=datetime.datetime.now())

    def __init__(self, *args, **kwargs):
        if 'meeting_id' in kwargs:
            self.meeting_id = kwargs.pop('meeting_id', None)
        super(MeetingsForm, self).__init__(*args, **kwargs)
        try:
            meeting = get_object_or_404(Meeting, id=self.meeting_id)
            self.initial['name'] = meeting.name
            self.initial['description'] = meeting.description
            self.initial['place'] = meeting.place
            self.initial['date'] = meeting.date.strftime('%Y-%m-%d')
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
