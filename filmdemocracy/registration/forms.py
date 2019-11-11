from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from PIL import Image

from filmdemocracy.registration.models import User


class SignupForm(UserCreationForm):
    agree_terms = forms.BooleanField(required=False, label='agree_terms')

    class Meta(UserCreationForm):
        model = User
        fields = ('email', 'username', 'password1', 'password2', 'agree_terms')

    def clean_agree_terms(self):
        agree_terms = self.cleaned_data['agree_terms']
        if not agree_terms:
            raise forms.ValidationError(_("You must agree to the terms and conditions to create an account."))
        return agree_terms


class AccountInfoForm(UserChangeForm):
    # TODO: profile_image validation
    updateImage = forms.BooleanField(widget=forms.HiddenInput(), required=False)
    x = forms.FloatField(widget=forms.HiddenInput(), required=False)
    y = forms.FloatField(widget=forms.HiddenInput(), required=False)
    width = forms.FloatField(widget=forms.HiddenInput(), required=False)
    height = forms.FloatField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = User
        fields = ['updateImage', 'profile_image', 'x', 'y', 'width', 'height', 'email', 'public_email']
        widgets = {
            'profile_image': forms.FileInput(attrs={
                'accept': 'image/*'  # this is not an actual validation! don't rely on that!
            })
        }

    def clean_profile_image(self):
        # TODO: club logo_image validation
        update_image = self.cleaned_data.get('updateImage')
        profile_image = self.cleaned_data['profile_image']
        if update_image:
            return profile_image
        else:
            return

    def save(self):
        user = super(AccountInfoForm, self).save()
        print(self)
        update_image = self.cleaned_data.get('updateImage')
        x = self.cleaned_data.get('x')
        y = self.cleaned_data.get('y')
        w = self.cleaned_data.get('width')
        h = self.cleaned_data.get('height')
        if update_image and x is not None and y is not None and w is not None and h is not None:
            image = Image.open(user.profile_image)
            cropped_image = image.crop((x, y, w+x, h+y))
            resized_image = cropped_image.resize((516, 516), Image.ANTIALIAS)
            resized_image.save(user.profile_image.path)
        return user
