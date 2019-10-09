from django.urls import include, path, re_path

from filmdemocracy.democracy.views import club as club_views
from filmdemocracy.democracy.views import film as film_views
from filmdemocracy.democracy.views import chat as chat_views
from filmdemocracy.democracy.views import meetings as meetings_views
from filmdemocracy.democracy.models import CLUB_ID_N_DIGITS, FILM_ID_N_DIGITS, MEETING_ID_N_DIGITS


app_name = 'democracy'


FULL_FILM_ID_N_DIGITS = CLUB_ID_N_DIGITS + FILM_ID_N_DIGITS
FULL_MEETINGS_ID_N_DIGITS = CLUB_ID_N_DIGITS + MEETING_ID_N_DIGITS


options_regexp = r'(?:&view=(?P<view_opt>[a-zA-Z_]+))?(?:&order=(?P<order_opt>[a-zA-Z_]+))?(?:&display=(?P<display_opt>[a-zA-Z_]+))?/?$'
club_regexp = r'(?P<club_id>[0-9]{{{club_id_n_digits}}})/'.format(club_id_n_digits=CLUB_ID_N_DIGITS)
film_regexp = r'(?P<film_id>[0-9]{{{full_film_id_n_digits}}})/'.format(full_film_id_n_digits=FULL_FILM_ID_N_DIGITS)
meeting_regexp = r'(?P<meeting_id>[0-9]{{{full_meetings_id_n_digits}}})/'.format(full_meetings_id_n_digits=FULL_MEETINGS_ID_N_DIGITS)


club_urlpatterns = [
    path(
        'club/create/',
        club_views.CreateClubView.as_view(template_name='democracy/edit_club_create.html'),
        name='create_club'
    ),
    path(
        'invitation_link/<uinviteridb64>/<uemailb64>/<uclubidb64>/',
        club_views.InviteNewMemberConfirmView.as_view(template_name='democracy/invite_new_member_confirm.html'),
        name='invite_new_member_confirm'
    ),
    re_path('club/' + club_regexp, include([
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
            'member/<str:user_id>/',
            club_views.ClubMemberDetailView.as_view(template_name='democracy/club_member_detail.html'),
            name='club_member_detail'
        ),
        path(
            'leave_club/',
            club_views.leave_club,
            name='leave_club'
        ),
        path(
            'self_demote/',
            club_views.self_demote,
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
            'ranking/participants/',
            club_views.RankingParticipantsView.as_view(template_name='democracy/ranking_participants.html'),
            name='ranking_participants'
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
    re_path('film/' + film_regexp, include([
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
            r'delete_comment/(?P<comment_id>[0-9]+)/' + options_regexp,
            film_views.delete_film_comment,
            name='delete_film_comment'
        ),
        re_path(
            r'(?P<film_slug>[a-z-]+)/' + options_regexp,
            film_views.FilmDetailView.as_view(template_name='democracy/film_detail.html'),
            name='film_detail'
        ),
        re_path(
            r'film_seen/' + options_regexp,
            film_views.FilmSeenView.as_view(template_name='democracy/candidate_films_seen.html'),
            name='film_seen'
        ),
        ])
    )
]


meetings_urlpatterns = [
    re_path('club/' + club_regexp + 'meetings/', include([
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
        re_path(meeting_regexp, include([
            path(
                'edit/',
                meetings_views.MeetingsEditView.as_view(template_name='democracy/meetings_form.html'),
                name='meetings_edit'
            ),
            path(
                'assistance/',
                meetings_views.meeting_assistance,
                name='meeting_assistance'
            ),
            path(
                'delete/',
                meetings_views.delete_meeting,
                name='delete_meeting'
            ),
            ])
        )
        ])
     )
]


chat_urlpatterns = [
    path(
        'chat/contacts/',
        chat_views.ChatContactsView.as_view(template_name='democracy/chat_contacts.html'),
        name='contacts'
    ),
    re_path('chat/club/' + club_regexp, include([
        path(
            '',
            chat_views.ChatClubView.as_view(template_name='democracy/chat_club.html'),
            name='chatclub'
        ),
        path(
            'post/',
            chat_views.post_in_chatclub,
            name='post_in_chatclub'
        ),
        path(
            'delete_post/<str:post_id>/',
            chat_views.delete_chatclub_post,
            name='delete_chatclub_post'
        ),
        ])
    ),
    path('chat/user/<str:chatuser_id>/', include([
        path(
            '',
            chat_views.ChatUsersView.as_view(template_name='democracy/chat_users.html'),
            name='chatusers'
        ),
        path(
            'post/',
            chat_views.post_in_chatusers,
            name='post_in_chatusers'
        ),
        path(
            'delete_post/<str:post_id>/',
            chat_views.delete_chatusers_post,
            name='delete_chatusers_post'
        ),
        ])
    )
]


urlpatterns = club_urlpatterns + film_urlpatterns + chat_urlpatterns + meetings_urlpatterns
