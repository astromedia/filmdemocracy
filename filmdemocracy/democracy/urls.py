from django.urls import include, path, re_path

from filmdemocracy.democracy.views import club as club_views
from filmdemocracy.democracy.views import film as film_views
from filmdemocracy.democracy.views import meetings as meetings_views


app_name = 'democracy'


club_urlpatterns = [
    path(
        'club/create/',
        club_views.CreateClubView.as_view(template_name='democracy/edit_club_create.html'),
        name='create_club'
    ),
    path(
        'invitation/<uuid:invitation_id>/',
        club_views.InviteNewMemberConfirmView.as_view(template_name='democracy/invite_new_member_confirm.html'),
        name='invite_new_member_confirm'
    ),
    path(
        'new_film_autocomplete/',
        club_views.NewFilmAutocompleteView.as_view(),
        name='new_film_autocomplete'
    ),
    path(
        'club/<str:club_id>/',
        club_views.ClubDetailView.as_view(template_name='democracy/club_detail.html'),
        name='club_detail'
    ),
    path(
        'club/<str:club_id>/edit_info/',
        club_views.EditClubInfoView.as_view(template_name='democracy/edit_club_info.html'),
        name='edit_club_info'
    ),
    path(
        'club/<str:club_id>/member/<uuid:member_id>/',
        club_views.ClubMemberDetailView.as_view(template_name='democracy/club_member_detail.html'),
        name='club_member_detail'
    ),
    path(
        'club/<str:club_id>/leave_club/',
        club_views.LeaveClubView.as_view(template_name='democracy/leave_club.html'),
        name='leave_club'
    ),
    path(
        'club/<str:club_id>/self_demote/',
        club_views.SelfDemoteView.as_view(template_name='democracy/self_demote.html'),
        name='self_demote'
    ),
    path(
        'club/<str:club_id>/kick_members/',
        club_views.KickMembersView.as_view(template_name='democracy/club_kick_members.html'),
        name='kick_members'
    ),
    path(
        'club/<str:club_id>/promote_members/',
        club_views.PromoteMembersView.as_view(template_name='democracy/club_promote_members.html'),
        name='promote_members'
    ),
    path(
        'club/<str:club_id>/ranking/generator/',
        club_views.RankingGeneratorView.as_view(template_name='democracy/ranking_generator.html'),
        name='ranking_generator'
    ),
    path(
        'club/<str:club_id>/ranking/results/',
        club_views.RankingResultsView.as_view(template_name='democracy/ranking_results.html'),
        name='ranking_results'
    ),
    path(
        'club/<str:club_id>/add_new_film/',
        club_views.AddNewFilmView.as_view(template_name='democracy/add_new_film.html'),
        name='add_new_film'
    ),
    path(
        'club/<str:club_id>/seen_films/',
        club_views.SeenFilmsView.as_view(template_name='democracy/seen_films_list.html'),
        name='seen_films'
    ),
    path(
        'club/<str:club_id>/invite_new_member/',
        club_views.InviteNewMemberView.as_view(template_name='democracy/invite_new_member.html'),
        name='invite_new_member'
    ),
    path(
        'club/<str:club_id>/candidate_films/',
        club_views.CandidateFilmsView.as_view(template_name='democracy/candidate_films_list.html'),
        name='candidate_films'
    )
]


film_urlpatterns = [
    path(
        'club/<str:club_id>/film/<str:film_public_id>/vote_film/',
        film_views.vote_film,
        name='vote_film'
    ),
    path(
        'club/<str:club_id>/film/<str:film_public_id>/delete_film/',
        film_views.delete_film,
        name='delete_film'
    ),
    path(
        'club/<str:club_id>/film/<str:film_public_id>/unsee_film/',
        film_views.unsee_film,
        name='unsee_film'
    ),
    path(
        'club/<str:club_id>/film/<str:film_public_id>/delete_vote/',
        film_views.delete_vote,
        name='delete_vote'
    ),
    path(
        'club/<str:club_id>/film/<str:film_public_id>/film_seen/',
        film_views.FilmSeenView.as_view(template_name='democracy/film_seen.html'),
        name='film_seen'
    ),
    path(
        'club/<str:club_id>/film/<str:film_public_id>/<slug:film_slug>',
        film_views.FilmDetailView.as_view(template_name='democracy/film_detail.html'),
        name='film_detail'
    )
]


meetings_urlpatterns = [
    path(
        'club/<str:club_id>/meetings/',
        meetings_views.MeetingsListView.as_view(template_name='democracy/meetings_list.html'),
        name='meetings_list'
    ),
    path(
        'club/<str:club_id>/meetings/new/',
        meetings_views.MeetingsNewView.as_view(template_name='democracy/meetings_form.html'),
        name='meetings_new'
    ),
    path(
        'club/<str:club_id>/meetings/<uuid:meeting_id>/edit/',
        meetings_views.MeetingsEditView.as_view(template_name='democracy/meetings_form.html'),
        name='meetings_edit'
    ),
    path(
        'club/<str:club_id>/meetings/<uuid:meeting_id>/assistance/',
        meetings_views.meeting_assistance,
        name='meeting_assistance'
    ),
    path(
        'club/<str:club_id>/meetings/<uuid:meeting_id>/delete/',
        meetings_views.delete_meeting,
        name='delete_meeting'
    )
]


urlpatterns = club_urlpatterns + film_urlpatterns + meetings_urlpatterns
