from django.urls import path
from django.contrib.auth import views as auth_views

from filmdemocracy.registration import views


app_name = 'registration'
urlpatterns = [
    path(
        'signup/',
        views.SignUpView.as_view(),
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
        'account_info/',
        views.AccountInfoView.as_view(),
        name='account_info'
    ),
    path(
        'account_info_edit/',
        views.AccountInfoEditView.as_view(),
        name='account_info_edit'
    ),
    path(
        'account_del/',
        views.account_del,
        name='account_del'
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
            html_email_template_name='registration/password_reset_email.html',
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