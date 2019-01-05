from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.files.images import get_image_dimensions
from django.utils.translation import gettext_lazy as _

from filmdemocracy.registration.models import User


class SignupForm(UserCreationForm):
    agree_terms = forms.BooleanField(required=False, label='agree_terms')

    class Meta(UserCreationForm):
        model = User
        fields = ('email', 'username', 'password1', 'password2',)

    def clean_agree_terms(self):
        agree_terms = self.cleaned_data['agree_terms']
        if not agree_terms:
            raise forms.ValidationError(
                _(f"You must agree to the "
                  f"terms and conditions to create an account.")
            )
        return agree_terms


class AccountInfoEditForm(UserChangeForm):

    class Meta:
        model = User
        fields = ['profile_image', 'email']

    def clean_profile_image(self):
        profile_image = self.cleaned_data['profile_image']

        # try:
        #     w, h = get_image_dimensions(profile_image)
        #
        #     # validate dimensions
        #     max_width = max_height = 200
        #     if w > max_width or h > max_height:
        #         raise forms.ValidationError(
        #             u'Please use an image that is '
        #             '%s x %s pixels or smaller.' % (max_width, max_height))
        #
        #     # validate content type
        #     main, sub = profile_image.content_type.split('/')
        #     if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
        #         raise forms.ValidationError(u'Please use a JPEG, '
        #                                     'GIF or PNG image.')
        #
        #     # validate file size
        #     if len(profile_image) > (200 * 1024):
        #         raise forms.ValidationError(
        #             u'Avatar file size may not exceed 200k.')
        #
        # except AttributeError:
        #     """
        #     Handles case when we are updating the user profile
        #     and do not supply a new avatar
        #     """
        #     pass

        return profile_image
