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


def process_imdb_url(form):
    """
    Validate that the url is a valid IMDb url and return IMDb id.
    """
    imdb_url = form.cleaned_data['imdb_url']
    try:
        if 'imdb' not in imdb_url:
            raise ValueError
        url_list = imdb_url.split('/')
        title_position = url_list.index('title')
        imdb_key = url_list[title_position + 1]
        if 'tt' not in imdb_key or len(imdb_key) is not 9:
            raise ValueError
        else:
            return imdb_key.replace('tt', '')
    except ValueError:
        raise forms.ValidationError(_("Invalid IMDb url."))


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


# class FilmAddNewForm(forms.ModelForm):
#     imdb_url = forms.CharField(
#         max_length=200,
#         label=_('IMDb url'),
#     )
#
#     class Meta:
#         model = Film
#         fields = ['imdb_url']
#
#     def __init__(self, *args, **kwargs):
#         self.club_id = kwargs.pop('club_id', None)
#         super(FilmAddNewForm, self).__init__(*args, **kwargs)
#
#     def clean_imdb_url(self):
#         imdb_key = process_imdb_url(self)
#         if Film.objects.filter(club=self.club_id, imdb_id=imdb_key, seen=False):
#             raise forms.ValidationError(
#                 _("That film is already in the candidate list!")
#             )
#         else:
#             return imdb_key


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
        self.film_id = kwargs.pop('film_id', None)
        club_members = kwargs.pop('club_members', None)
        super(FilmSeenForm, self).__init__(*args, **kwargs)
        self.fields['members'].queryset = club_members

    def clean_seen_date(self):
        seen_date = self.cleaned_data['seen_date']
        if not seen_date:
            raise forms.ValidationError(
                _("You must set a date.")
            )
        film = get_object_or_404(Film, pk=self.film_id)
        if seen_date < film.pub_date.date():
            raise forms.ValidationError(
                _("You can't see films before they were proposed!")
            )
        elif seen_date > timezone.now().date():
            raise forms.ValidationError(
                _("Time travelling to the future is not possible (yet).")
            )
        else:
            return seen_date

    def clean_members(self):
        members = self.cleaned_data['members']
        if not members:
            raise forms.ValidationError(
                _("Someone must have seen it... right?")
            )
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

    def send_mail(self, subject_template_name, email_template_name,
                  html_email_template_name, context, from_email, to_email):
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines:
        # http://nyphp.org/phundamentals/8_Preventing-Email-Header-Injection
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')
        email_message.send()

    def save(self,
             domain_override=None,
             subject_template_name='',
             email_template_name='',
             html_email_template_name='',
             extra_email_context=None,
             use_https=False, from_email=None, request=None):
        user = request.user
        email = self.cleaned_data["email"]
        invitation_text = self.cleaned_data["invitation_text"]
        club = get_object_or_404(Club, pk=self.club_id)
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        context = {
            'user': user,
            'club': club,
            'email': email,
            'invitation_text': invitation_text,
            'domain': domain,
            'site_name': site_name,
            'uinviterid': urlsafe_base64_encode(force_bytes(user.pk)),
            'uclubid': urlsafe_base64_encode(force_bytes(club.pk)),
            'uemail': urlsafe_base64_encode(force_bytes(email)),
            'protocol': 'https' if use_https else 'http',
            **(extra_email_context or {}),
        }
        self.send_mail(
            subject_template_name, email_template_name,
            html_email_template_name, context, from_email, email
        )


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
    spam_opts = forms.ChoiceField(choices=(('all', ""), ('interested', ""), ('noone', "")),
                                  label='spam_opts', required=False)

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
            self.initial['date'] = meeting.date
            self.initial['time_start'] = meeting.time_start
            self.initial['time_end'] = meeting.time_end
        except AttributeError:
            pass

    class Meta:
        model = Meeting
        fields = ['name', 'description', 'place', 'date', 'time_start', 'time_end', 'send_spam', 'spam_opts']

    def clean_date(self):
        date = self.cleaned_data['date']
        if date < timezone.now().date():
            raise forms.ValidationError(
                _("No much sense on planning now a meeting on the past, sorry.")
            )
        return date

    def clean_time_start(self):
        time_start = self.cleaned_data['time_start']
        if time_start:
            date = self.cleaned_data['date']
            if date == timezone.now().date():
                time_start = self.cleaned_data['time_start']
                if time_start < timezone.now().time():
                    raise forms.ValidationError(
                        _("Meetings can't start before they are proposed, sorry.")
                    )
        return self.cleaned_data['time_start']

    @staticmethod
    def send_mail(subject_template_name, email_template_name,
                  html_email_template_name, context, from_email, to_email):
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines:
        # http://nyphp.org/phundamentals/8_Preventing-Email-Header-Injection
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')
        email_message.send()

    def spam_members(self,
                     spammable_members,
                     domain_override=None,
                     subject_template_name='',
                     email_template_name='',
                     html_email_template_name='',
                     extra_email_context=None,
                     use_https=False, from_email=None, request=None):
        user = request.user
        name = self.cleaned_data['name']
        description = self.cleaned_data['description']
        place = self.cleaned_data['place']
        date = self.cleaned_data['date']
        time_start = self.cleaned_data['time_start']
        time_end = self.cleaned_data['time_end']
        club = get_object_or_404(Club, pk=self.club_id)
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        context = {
            'organizer': user,
            'club': club,
            'name': name,
            'description': description,
            'place': place,
            'date': date,
            'time_start': time_start,
            'time_end': time_end,
            'domain': domain,
            'site_name': site_name,
            'protocol': 'https' if use_https else 'http',
            **(extra_email_context or {}),
        }
        for member in spammable_members:
            self.send_mail(subject_template_name, email_template_name, html_email_template_name,
                           context, from_email, member.email)
