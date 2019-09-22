from django.urls import path

from filmdemocracy.democracy import views

app_name = 'democracy'
urlpatterns = [
    path(
        'notification_dispatcher/',
        views.notification_dispatcher,
        name='notification_dispatcher'
    ),
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
        'club/<str:club_id>/member/<str:user_id>/',
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
        '<str:club_id>/candidate_films/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.CandidateFilmsView.as_view(
            template_name='democracy/candidate_films_list.html'
        ),
        name='candidate_films'
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
            template_name='democracy/ranking_films_participants.html'
        ),
        name='participants'
    ),
    path(
        '<str:club_id>/candidate_films/vote_results/',
        views.VoteResultsView.as_view(
            template_name='democracy/ranking_films_vote_results.html'
        ),
        name='vote_results'
    ),
    path(
        'club/<str:club_id>/add_new_film/',
        views.AddNewFilmView.as_view(
            template_name='democracy/add_new_film.html'
        ),
        name='add_new_film'
    ),
    # path(
    #     '<str:club_id>/add_new_film/add/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
    #     views.add_new_film,
    #     name='add_new_film'
    # ),
    path(
        '<str:club_id>/film/<str:film_id>/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.FilmDetailView.as_view(
            template_name='democracy/film_detail.html'
        ),
        name='film_detail'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/vote_film/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.vote_film,
        name='vote_film'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/delete_vote/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.delete_vote,
        name='delete_vote'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/comment_film/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.comment_film,
        name='comment_film'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/delete_comment/<str:comment_id>&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.delete_film_comment,
        name='delete_film_comment'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/delete_film/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.delete_film,
        name='delete_film'
    ),
    path(
        '<str:club_id>/film/<str:film_id>/unsee_film/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.unsee_film,
        name='unsee_film'
    ),
    # path(
    #     '<str:club_id>/film/<str:film_id>/update_film_data/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
    #     views.update_film_data,
    #     name='update_film_data'
    # ),
    path(
        '<str:club_id>/film/<str:film_id>/add_filmaffinity_url/&view=<str:view_option>&order=<str:order_option>&display=<str:display_option>/',
        views.add_filmaffinity_url,
        name='add_filmaffinity_url'
    ),
    path(
        '<str:club_id>/seen_films/',
        views.SeenFilmsView.as_view(
            template_name='democracy/seen_films_list.html'
        ),
        name='seen_films'
    ),
    path(
        'club/<str:club_id>/invite_new_member/',
        views.InviteNewMemberView.as_view(
            template_name='democracy/invite_new_member.html'
        ),
        name='invite_new_member'
    ),
    path(
        'invitation_link/<uinviteridb64>/<uemailb64>/<uclubidb64>/',
        views.InviteNewMemberConfirmView.as_view(
            template_name='democracy/invite_new_member_confirm.html'
        ),
        name='invite_new_member_confirm'
    ),
    path(
        'club/<str:club_id>/meetings/organize_new/',
        views.MeetingsNewView.as_view(
            template_name='democracy/meetings_form.html'
        ),
        name='meetings_new'
    ),
    path(
        'club/<str:club_id>/meetings/<str:meeting_id>/assistance/',
        views.meeting_assistance,
        name='meeting_assistance'
    ),
    path(
        'club/<str:club_id>/meetings/<str:meeting_id>/delete/',
        views.delete_meeting,
        name='delete_meeting'
    ),
    path(
        'club/<str:club_id>/meetings/<str:meeting_id>/edit/',
        views.MeetingsEditView.as_view(
            template_name='democracy/meetings_form.html'
        ),
        name='meetings_edit'
    ),
    path(
        'club/<str:club_id>/meetings/list/',
        views.MeetingsListView.as_view(
            template_name='democracy/meetings_list.html'
        ),
        name='meetings_list'
    ),
    path(
        'chat/club/<str:club_id>/',
        views.ChatClubView.as_view(
            template_name='democracy/chat_club.html'
        ),
        name='chatclub'
    ),
    path(
        'chat/club/<str:club_id>/post/',
        views.post_in_chatclub,
        name='post_in_chatclub'
    ),
    path(
        'chat/club/<str:club_id>/delete_post/<str:post_id>/',
        views.delete_chatclub_post,
        name='delete_chatclub_post'
    ),
    path(
        'chat/contacts/',
        views.ChatContactsView.as_view(
            template_name='democracy/chat_contacts.html'
        ),
        name='contacts'
    ),
    path(
        'chat/user/<str:chatuser_id>/',
        views.ChatUsersView.as_view(
            template_name='democracy/chat_users.html'
        ),
        name='chatusers'
    ),
    path(
        'chat/user/<str:chatuser_id>/post/',
        views.post_in_chatusers,
        name='post_in_chatusers'
    ),
    path(
        'chat/user/<str:chatuser_id>/delete_post/<str:post_id>/',
        views.delete_chatusers_post,
        name='delete_chatusers_post'
    ),
]
