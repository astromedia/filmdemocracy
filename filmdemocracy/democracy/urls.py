from django.urls import path

from filmdemocracy.democracy import views


app_name = 'democracy'
urlpatterns = [
    path(
        '<int:club_id>/',
        views.CandidateFilmsView.as_view(),
        name='candidate_films'
    ),
    path(
        '<int:club_id>/add_new_film/',
        views.AddNewFilmView.as_view(),
        name='add_new_film'
    ),
    path(
        '<int:club_id>/film/<int:film_id>/',
        views.FilmDetailView.as_view(),
        name='film_detail'
    ),
    path(
        '<int:club_id>/film/<int:film_id>/vote_film/',
        views.vote_film,
        name='vote_film'
    ),
    path(
        '<int:club_id>/film/<int:film_id>/film_add_faff/',
        views.FilmAddFilmAffView.as_view(),
        name='film_add_faff'
    ),
    path(
        '<int:club_id>/film/<int:film_id>/delete_film/',
        views.delete_film,
        name='delete_film'
    ),
    path(
        '<int:club_id>/film/<int:film_id>/film_seen/',
        views.FilmSeenView.as_view(),
        name='film_seen'
    ),
    path(
        '<int:club_id>/film/<int:film_id>/unsee_film/',
        views.unsee_film,
        name='unsee_film'
    ),
    path(
        '<int:club_id>/participants/',
        views.ParticipantsView.as_view(),
        name='participants'
    ),
    path(
        '<int:club_id>/vote_results/',
        views.VoteResultsView.as_view(),
        name='vote_results'
    ),
]
