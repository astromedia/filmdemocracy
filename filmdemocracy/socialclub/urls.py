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
    path(
        'club/<int:pk>/edit_info/',
        views.EditClubInfoView.as_view(
            template_name='socialclub/edit_club_info.html'
        ),
        name='edit_club_info'
    ),
    path(
        'club/<int:pk>/edit_description/',
        views.EditClubDescriptionView.as_view(
            template_name='socialclub/edit_club_description.html'
        ),
        name='edit_club_description'
    ),
    path(
        'club/<int:pk>/',
        views.ClubDetailView.as_view(
            template_name='socialclub/club_detail.html'
        ),
        name='club_detail'
    ),
    path(
        'club/<int:club_id>/leave_club/',
        views.leave_club,
        name='leave_club'
    ),
    path(
        'club/<int:club_id>/selfdemote/',
        views.selfdemote,
        name='selfdemote'
    ),
    path(
        'club/<int:pk>/kick_members/',
        views.KickMembersView.as_view(
            template_name='socialclub/kick_members.html'
        ),
        name='kick_members'
    ),
    path(
        'club/<int:pk>/promote_members_to_admin/',
        views.PromoteMembersToAdminView.as_view(
            template_name='socialclub/promote_members_to_admin.html'
        ),
        name='promote_members_to_admin'
    ),
]
