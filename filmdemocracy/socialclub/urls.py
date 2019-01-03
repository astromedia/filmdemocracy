from django.urls import path

from filmdemocracy.socialclub import views


app_name = 'socialclub'
urlpatterns = [
    path(
        'create_club/',
        views.CreateClubView.as_view(
            template_name='socialclub/create_club.html'
        ),
        name='create_club'
    ),
]
