from django.urls import path

from filmdemocracy.core import views


app_name = 'core'
urlpatterns = [
    path(
        '',
        views.HomeView.as_view(template_name='core/home.html'),
        name='home'
    ),
    path(
        'terms_and_conditions/',
        views.TermsAndConditionsView.as_view(template_name='core/terms_and_conditions.html'),
        name='terms_and_conditions'
    ),
    path(
        'notification_dispatcher/<str:ntf_type>/<str:ntf_club_id>/<str:ntf_object_id>/',
        views.notification_dispatcher,
        name='notification_dispatcher'
    ),
    path(
        'notification_cleaner/',
        views.notification_cleaner,
        name='notification_cleaner'
    ),
]
