from filmdemocracy.core.utils import NotificationsHelper
from filmdemocracy.democracy.models import Club


def notifications(request):
    notifications_helper = NotificationsHelper(request)
    if notifications_helper.check_user_is_anonymous():
        return {}
    notifications_helper.process_notifications()
    return {'notifications': {
        'list': notifications_helper.messages,
        'unread_count': notifications_helper.unread_count}
    }


def club_context(request):
    if 'club_id' in request.resolver_match.kwargs:
        club = Club.objects.get(id=request.resolver_match.kwargs['club_id'])
        if club:
            return {
                'club': club,
                'club_members': club.members.filter(is_active=True),
                'club_admins': club.admin_members.filter(is_active=True),
            }
    return {}
