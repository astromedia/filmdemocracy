from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from filmdemocracy.registration.models import User


class SignupForm(UserCreationForm):
    agree_terms = forms.BooleanField(required=False, label='agree_terms')

    class Meta(UserCreationForm):
        model = User
        fields = ('email', 'username', 'password1', 'password2', 'agree_terms')

    def clean_agree_terms(self):
        agree_terms = self.cleaned_data['agree_terms']
        if not agree_terms:
            raise forms.ValidationError(
                _(f"You must agree to the "
                  f"terms and conditions to create an account.")
            )
        return agree_terms


class AccountInfoEditForm(UserChangeForm):
    # TODO: profile_image validation

    class Meta:
        model = User
        fields = ['profile_image', 'email']
