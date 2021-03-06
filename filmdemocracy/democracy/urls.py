from django.urls import include, path, re_path

from filmdemocracy.democracy.views import club as club_views
from filmdemocracy.democracy.views import film as film_views
from filmdemocracy.democracy.views import meetings as meetings_views


app_name = 'democracy'


options_regexp = r'(?:(?P<options_string>[0-9a-zA-Z_&=\?]+))?$'


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
    path('club/<str:club_id>/', include([
        path(
            '',
            club_views.ClubDetailView.as_view(template_name='democracy/club_detail.html'),
            name='club_detail'
        ),
        path(
            'edit_info/',
            club_views.EditClubInfoView.as_view(template_name='democracy/edit_club_info.html'),
            name='edit_club_info'
        ),
        path(
            'edit_panel/',
            club_views.EditClubPanelView.as_view(template_name='democracy/edit_club_panel.html'),
            name='edit_club_panel'
        ),
        path(
            'member/<uuid:member_id>/',
            club_views.ClubMemberDetailView.as_view(template_name='democracy/club_member_detail.html'),
            name='club_member_detail'
        ),
        path(
            'leave_club/',
            club_views.LeaveClubView.as_view(template_name='democracy/leave_club.html'),
            name='leave_club'
        ),
        path(
            'self_demote/',
            club_views.SelfDemoteView.as_view(template_name='democracy/self_demote.html'),
            name='self_demote'
        ),
        path(
            'kick_members/',
            club_views.KickMembersView.as_view(template_name='democracy/club_kick_members.html'),
            name='kick_members'
        ),
        path(
            'promote_members/',
            club_views.PromoteMembersView.as_view(template_name='democracy/club_promote_members.html'),
            name='promote_members'
        ),
        path(
            'ranking/generator/',
            club_views.RankingGeneratorView.as_view(template_name='democracy/ranking_generator.html'),
            name='ranking_generator'
        ),
        path(
            'ranking/results/',
            club_views.RankingResultsView.as_view(template_name='democracy/ranking_results.html'),
            name='ranking_results'
        ),
        path(
            'add_new_film/',
            club_views.AddNewFilmView.as_view(template_name='democracy/add_new_film.html'),
            name='add_new_film'
        ),
        path(
            'seen_films/',
            club_views.SeenFilmsView.as_view(template_name='democracy/seen_films_list.html'),
            name='seen_films'
        ),
        path(
            'invite_new_member/',
            club_views.InviteNewMemberView.as_view(template_name='democracy/invite_new_member.html'),
            name='invite_new_member'
        ),
        re_path(
            r'candidate_films/' + options_regexp,
            club_views.CandidateFilmsView.as_view(template_name='democracy/candidate_films_list.html'),
            name='candidate_films'
        ),
        ])
     )
]


film_urlpatterns = [
    path('club/<str:club_id>/film/<str:film_public_id>/', include([
        re_path(
            r'vote_film/' + options_regexp,
            film_views.vote_film,
            name='vote_film'
        ),
        re_path(
            r'delete_film/' + options_regexp,
            film_views.delete_film,
            name='delete_film'
        ),
        re_path(
            r'unsee_film/' + options_regexp,
            film_views.unsee_film,
            name='unsee_film'
        ),
        re_path(
            r'add_filmaffinity_url/' + options_regexp,
            film_views.add_filmaffinity_url,
            name='add_filmaffinity_url'
        ),
        re_path(
            r'delete_vote/' + options_regexp,
            film_views.delete_vote,
            name='delete_vote'
        ),
        re_path(
            r'comment_film/' + options_regexp,
            film_views.comment_film,
            name='comment_film'
        ),
        re_path(
            r'delete_comment/(?P<comment_id>[0-9a-f-]+)/' + options_regexp,
            film_views.delete_film_comment,
            name='delete_film_comment'
        ),
        re_path(
            r'film_seen/' + options_regexp,
            film_views.FilmSeenView.as_view(template_name='democracy/film_seen.html'),
            name='film_seen'
        ),
        re_path(
            r'(?P<film_slug>[\w-]+)/' + options_regexp,
            film_views.FilmDetailView.as_view(template_name='democracy/film_detail.html'),
            name='film_detail'
        ),
        ])
    )
]


meetings_urlpatterns = [
    path('club/<str:club_id>/meetings/', include([
        path(
            '',
            meetings_views.MeetingsListView.as_view(template_name='democracy/meetings_list.html'),
            name='meetings_list'
        ),
        path(
            'new/',
            meetings_views.MeetingsNewView.as_view(template_name='democracy/meetings_form.html'),
            name='meetings_new'
        ),
        path(
            '<uuid:meeting_id>/edit/',
            meetings_views.MeetingsEditView.as_view(template_name='democracy/meetings_form.html'),
            name='meetings_edit'
        ),
        path(
            '<uuid:meeting_id>/assistance/',
            meetings_views.meeting_assistance,
            name='meeting_assistance'
        ),
        path(
            '<uuid:meeting_id>/delete/',
            meetings_views.delete_meeting,
            name='delete_meeting'
        ),
        ])
     )
]


urlpatterns = club_urlpatterns + film_urlpatterns + meetings_urlpatterns
