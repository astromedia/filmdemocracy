from django.urls import path

from filmdemocracy.democracy.views import club as club_views
from filmdemocracy.democracy.views import film as film_views
from filmdemocracy.democracy.views import chat as chat_views
from filmdemocracy.democracy.views import meetings as meetings_views


app_name = 'democracy'


candidate_films_view_options = '&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/'


club_urlpatterns = [
    path(
        'club/create/',
        club_views.CreateClubView.as_view(template_name='democracy/edit_club_create.html'),
        name='create_club'
    ),
    path(
        'club/<str:club_id>/edit_info/',
        club_views.EditClubInfoView.as_view(template_name='democracy/edit_club_info.html'),
        name='edit_club_info'
    ),
    path(
        'club/<str:club_id>/edit_panel/',
        club_views.EditClubPanelView.as_view(template_name='democracy/edit_club_panel.html'),
        name='edit_club_panel'
    ),
    path(
        'club/<str:club_id>/',
        club_views.ClubDetailView.as_view(template_name='democracy/club_detail.html'),
        name='club_detail'
    ),
    path(
        'club/<str:club_id>/member/<str:user_id>/',
        club_views.ClubMemberDetailView.as_view(template_name='democracy/club_member_detail.html'),
        name='club_member_detail'
    ),
    path(
        'club/<str:club_id>/leave_club/',
        club_views.leave_club,
        name='leave_club'
    ),
    path(
        'club/<str:club_id>/self_demote/',
        club_views.self_demote,
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
        'club/<str:club_id>/candidate_films/' + candidate_films_view_options,
        club_views.CandidateFilmsView.as_view(template_name='democracy/candidate_films_list.html'),
        name='candidate_films'
    ),
    path(
        'club/<str:club_id>/ranking/participants/',
        club_views.RankingParticipantsView.as_view(template_name='democracy/ranking_participants.html'),
        name='ranking_participants'
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
        'invitation_link/<uinviteridb64>/<uemailb64>/<uclubidb64>/',
        club_views.InviteNewMemberConfirmView.as_view(template_name='democracy/invite_new_member_confirm.html'),
        name='invite_new_member_confirm'
    ),
]


film_urlpatterns = [
    path(
        'film/<str:film_id>/<str:film_slug>/' + candidate_films_view_options,
        film_views.FilmDetailView.as_view(template_name='democracy/film_detail.html'),
        name='film_detail'
    ),
    path(
        'film/<str:film_id>/vote_film/' + candidate_films_view_options,
        film_views.vote_film,
        name='vote_film'
    ),
    path(
        'film/<str:film_id>/delete_vote/' + candidate_films_view_options,
        film_views.delete_vote,
        name='delete_vote'
    ),
    path(
        'film/<str:film_id>/comment_film/' + candidate_films_view_options,
        film_views.comment_film,
        name='comment_film'
    ),
    path(
        'film/<str:film_id>/delete_comment/<str:comment_id>/' + candidate_films_view_options,
        film_views.delete_film_comment,
        name='delete_film_comment'
    ),
    path(
        'film/<str:film_id>/delete_film/' + candidate_films_view_options,
        film_views.delete_film,
        name='delete_film'
    ),
    path(
        'film/<str:film_id>/unsee_film/' + candidate_films_view_options,
        film_views.unsee_film,
        name='unsee_film'
    ),
    path(
        'film/<str:film_id>/add_filmaffinity_url/' + candidate_films_view_options,
        film_views.add_filmaffinity_url,
        name='add_filmaffinity_url'
    ),
    path(
        'film/<str:film_id>/<str:film_slug>/film_seen',
        film_views.FilmSeenView.as_view(template_name='democracy/candidate_films_seen.html'),
        name='film_seen'
    ),
]


meetings_urlpatterns = [
    path(
        'club/<str:club_id>/meetings/new',
        meetings_views.MeetingsNewView.as_view(template_name='democracy/meetings_form.html'),
        name='meetings_new'
    ),
    path(
        'club/<str:club_id>/meetings/<str:meeting_id>/edit/',
        meetings_views.MeetingsEditView.as_view(template_name='democracy/meetings_form.html'),
        name='meetings_edit'
    ),
    path(
        'club/<str:club_id>/meetings/',
        meetings_views.MeetingsListView.as_view(template_name='democracy/meetings_list.html'),
        name='meetings_list'
    ),
    path(
        'club/<str:club_id>/meetings/<str:meeting_id>/assistance/',
        meetings_views.meeting_assistance,
        name='meeting_assistance'
    ),
    path(
        'club/<str:club_id>/meetings/<str:meeting_id>/delete/',
        meetings_views.delete_meeting,
        name='delete_meeting'
    ),
]


chat_urlpatterns = [
    path(
        'chat/club/<str:club_id>/',
        chat_views.ChatClubView.as_view(template_name='democracy/chat_club.html'),
        name='chatclub'
    ),
    path(
        'chat/club/<str:club_id>/post/',
        chat_views.post_in_chatclub,
        name='post_in_chatclub'
    ),
    path(
        'chat/club/<str:club_id>/delete_post/<str:post_id>/',
        chat_views.delete_chatclub_post,
        name='delete_chatclub_post'
    ),
    path(
        'chat/contacts/',
        chat_views.ChatContactsView.as_view(template_name='democracy/chat_contacts.html'),
        name='contacts'
    ),
    path(
        'chat/user/<str:chatuser_id>/',
        chat_views.ChatUsersView.as_view(template_name='democracy/chat_users.html'),
        name='chatusers'
    ),
    path(
        'chat/user/<str:chatuser_id>/post/',
        chat_views.post_in_chatusers,
        name='post_in_chatusers'
    ),
    path(
        'chat/user/<str:chatuser_id>/delete_post/<str:post_id>/',
        chat_views.delete_chatusers_post,
        name='delete_chatusers_post'
    ),
]


urlpatterns = club_urlpatterns + film_urlpatterns + chat_urlpatterns + meetings_urlpatterns
