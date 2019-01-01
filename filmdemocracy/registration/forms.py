from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.files.images import get_image_dimensions

from filmdemocracy.registration.models import User, Club


class SignupForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = User
        fields = ('email', 'username', 'password1', 'password2')


class AccountInfoEditForm(UserChangeForm):

    class Meta:
        model = User
        fields = ['profile_image', 'email']

    def clean_profile_image(self):
        profile_image = self.cleaned_data['profile_image']

        try:
            w, h = get_image_dimensions(profile_image)

            # validate dimensions
            max_width = max_height = 200
            if w > max_width or h > max_height:
                raise forms.ValidationError(
                    u'Please use an image that is '
                    '%s x %s pixels or smaller.' % (max_width, max_height))

            # validate content type
            main, sub = profile_image.content_type.split('/')
            if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
                raise forms.ValidationError(u'Please use a JPEG, '
                                            'GIF or PNG image.')

            # validate file size
            if len(profile_image) > (200 * 1024):
                raise forms.ValidationError(
                    u'Avatar file size may not exceed 200k.')

        except AttributeError:
            """
            Handles case when we are updating the user profile
            and do not supply a new avatar
            """
            pass

        return profile_image


class CreateClubForm(forms.ModelForm):

    class Meta:
        model = Club
        fields = ['name', 'image', 'description']
