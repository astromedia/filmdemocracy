from django.urls import path

from filmdemocracy.chat import views


app_name = 'chat'


urlpatterns = [
    path(
        'contacts/',
        views.ChatContactsView.as_view(template_name='democracy/chat_contacts.html'),
        name='contacts'
    ),
    path(
        'club/<str:club_id>/',
        views.ChatClubView.as_view(template_name='democracy/chat_club.html'),
        name='chat_club'
    ),
    path(
        'club/<str:club_id>/post/',
        views.post_in_chat_club,
        name='post_in_chat_club'
    ),
    path(
        'club/<str:club_id>/delete_post/<uuid:post_id>/',
        views.delete_chat_club_post,
        name='delete_chat_club_post'
    ),
    path(
        'user/<uuid:chat_user_id>/',
        views.ChatUsersView.as_view(template_name='democracy/chat_users.html'),
        name='chat_users'
    ),
    path(
        'user/<uuid:chat_user_id>/post/',
        views.post_in_chat_users,
        name='post_in_chat_users'
    ),
    path(
        'user/<uuid:chat_user_id>/delete_post/<uuid:post_id>/',
        views.delete_chat_users_post,
        name='delete_chat_users_post'
    ),
]
