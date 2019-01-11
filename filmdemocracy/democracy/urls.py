from django.urls import path

from filmdemocracy.democracy import views


app_name = 'democracy'
urlpatterns = [
    path(
        'club/create_club/',
        views.CreateClubView.as_view(
            template_name='democracy/edit_club_create.html'
        ),
        name='create_club'
    ),
    path(
        'club/<str:club_id>/edit_info/',
        views.EditClubInfoView.as_view(
            template_name='democracy/edit_club_info.html'
        ),
        name='edit_club_info'
    ),
    path(
        'club/<str:club_id>/edit_panel/',
        views.EditClubPanelView.as_view(
            template_name='democracy/edit_club_panel.html'
        ),
        name='edit_club_panel'
    ),
    path(
        'club/<str:club_id>/',
        views.ClubDetailView.as_view(
            template_name='democracy/club_detail.html'
        ),
        name='club_detail'
    ),
    path(
        'club/<str:club_id>/member/<str:user_id>',
        views.ClubMemberDetailView.as_view(
            template_name='democracy/club_member_detail.html'
        ),
        name='club_member_detail'
    ),
    path(
        'club/<str:club_id>/leave_club/',
        views.leave_club,
        name='leave_club'
    ),
    path(
        'club/<str:club_id>/self_demote/',
        views.self_demote,
        name='self_demote'
    ),
    path(
        'club/<str:club_id>/kick_members/',
        views.KickMembersView.as_view(
            template_name='democracy/club_kick_members.html'
        ),
        name='kick_members'
    ),
    path(
        'club/<str:club_id>/promote_members/',
        views.PromoteMembersView.as_view(
            template_name='democracy/club_promote_members.html'
        ),
        name='promote_members'
    ),
    path(
        '<str:club_id>/candidate_films/',
        views.CandidateFilmsView.as_view(
            template_name='democracy/candidate_films_list.html'
        ),
        name='candidate_films'
    ),
    path(
        '<str:club_id>/candidate_films/seen_selection/',
        views.FilmSeenSelectionView.as_view(
            template_name='democracy/candidate_films_seen_selection.html'
        ),
        name='film_seen_selection'
    ),
    path(
        '<str:club_id>/candidate_films/film_seen/<str:film_id>/',
        views.FilmSeenView.as_view(
            template_name='democracy/candidate_films_seen.html'
        ),
        name='film_seen'
    ),
    path(
        '<str:club_id>/candidate_films/participants/',
        views.ParticipantsView.as_view(
            template_name='democracy/candidate_films_participants.html'
        ),
        name='participants'
    ),
    path(
        '<str:club_id>/candidate_films/vote_results/',
        views.VoteResultsView.as_view(
            template_name='democracy/candidate_films_vote_results.html'
        ),
        name='vote_results'
    ),
    path(
        '<str:club_id>/candidate_films/add_new/',
        views.AddNewFilmView.as_view(
            template_name='democracy/candidate_films_add_new.html'
        ),
        name='add_new_film'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/',
        views.FilmDetailView.as_view(
            template_name='democracy/film_detail.html'
        ),
        name='film_detail'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/vote_film/',
        views.vote_film,
        name='vote_film'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/film_add_faff/',
        views.FilmAddFilmAffView.as_view(
            template_name='democracy/film_add_faff.html'
        ),
        name='film_add_faff'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/delete_film/',
        views.delete_film,
        name='delete_film'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/unsee_film/',
        views.unsee_film,
        name='unsee_film'
    ),
]
