from django import forms
from django.core.files.images import get_image_dimensions

from filmdemocracy.socialclub.models import Club


class CreateClubForm(forms.ModelForm):

    class Meta:
        model = Club
        fields = ['name', 'image', 'short_description']

    def clean_image(self):
        image = self.cleaned_data['image']

        # try:
        #     w, h = get_image_dimensions(image)
        #
        #     # validate dimensions
        #     max_width = max_height = 200
        #     if w > max_width or h > max_height:
        #         raise forms.ValidationError(
        #             u'Please use an image that is '
        #             '%s x %s pixels or smaller.' % (max_width, max_height))
        #
        #     # validate content type
        #     main, sub = image.content_type.split('/')
        #     if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
        #         raise forms.ValidationError(u'Please use a JPEG, '
        #                                     'GIF or PNG image.')
        #
        #     # validate file size
        #     if len(image) > (200 * 1024):
        #         raise forms.ValidationError(
        #             u'Avatar file size may not exceed 200k.')
        #
        # except AttributeError:
        #     """
        #     Handles case when we are updating the user profile
        #     and do not supply a new avatar
        #     """
        #     pass

        return image
