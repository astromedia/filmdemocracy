from django.contrib.auth import views as auth_views
from django.urls import path

from filmdemocracy.registration import views


app_name = 'registration'
urlpatterns = [
    path(
        'signup/',
        views.SignUpView.as_view(
            template_name='registration/user_signup.html'
        ),
        name='user_signup'
    ),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/user_login.html'
        ),
        name='user_login'
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='user_logout'
    ),
    path(
        'account/info/',
        views.AccountInfoView.as_view(
            template_name='registration/account_info.html'
        ),
        name='account_info'
    ),
    path(
        'account/delete/',
        views.account_delete,
        name='account_delete'
    ),
    path(
        'password_change/',
        auth_views.PasswordChangeView.as_view(
            success_url='/registration/password_change/done/',
            template_name='registration/password_change.html'
        ),
        name='password_change'
    ),
    path(
        'password_change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='registration/password_change_done.html'
        ),
        name='password_change_done'
    ),
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            success_url='/registration/password_reset/done/',
            subject_template_name='registration/emails/password_reset_subject.txt',
            email_template_name='registration/emails/password_reset_email.html',
            html_email_template_name='registration/emails/password_reset_email_html.html',
            template_name='registration/password_reset.html'
        ),
        name='password_reset'
    ),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'password_reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            success_url='/registration/password_reset/complete/',
            template_name='registration/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),
    path(
        'password_reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]
