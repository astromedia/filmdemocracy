from django.urls import path

from filmdemocracy.democracy import views


app_name = 'democracy'
urlpatterns = [
    path(
        '',
        views.FilmListView.as_view(),
        name='film_list'
    ),
    path(
        'film_add_new/',
        views.FilmAddNewView.as_view(),
        name='film_add_new'
    ),
    path(
        '<int:pk>/',
        views.FilmDetailView.as_view(),
        name='film_detail'
    ),
    path(
        '<int:film_id>/vote_film/',
        views.vote_film,
        name='vote_film'
    ),
    path(
        '<int:pk>/film_delete_confirm/',
        views.FilmDeleteView.as_view(),
        name='film_delete'
    ),
    path(
        '<int:pk>/film_seen/',
        views.FilmSeenView.as_view(),
        name='film_seen'
    ),
    path(
        '<int:film_id>/unsee_film/',
        views.unsee_film,
        name='unsee_film'
    ),
    path(
        'participants/',
        views.ParticipantsView.as_view(),
        name='participants'
    ),
    path(
        'vote_results/',
        views.VoteResultsView.as_view(),
        name='vote_results'
    ),
]
