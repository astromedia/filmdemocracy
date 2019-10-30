from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from filmdemocracy.registration import forms
from filmdemocracy.registration.models import User


class CustomUserAdmin(UserAdmin):
    add_form = forms.SignupForm
    form = forms.AccountInfoForm
    model = User
    list_display = ['email', 'username',]


admin.site.register(User, UserAdmin)
