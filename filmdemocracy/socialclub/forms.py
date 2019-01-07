from django import forms

from filmdemocracy.socialclub.models import Club
from filmdemocracy.registration.models import User


class CreateClubForm(forms.ModelForm):

    class Meta:
        model = Club
        fields = ['name', 'logo', 'short_description']

    def clean_logo(self):
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
        club_members = kwargs.pop('club_members', None)
        super(KickMembersForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = club_members


class PromoteMembersToAdminForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.filter(pk=0),
        required=False
    )

    class Meta:
        model = Club
        fields = ['members']

    def __init__(self, *args, **kwargs):
        club_members = kwargs.pop('club_members', None)
        super(PromoteMembersToAdminForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = club_members
