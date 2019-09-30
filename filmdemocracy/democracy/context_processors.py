from filmdemocracy.democracy.utils import NotificationsHelper


def notifications(request):
    notifications_helper = NotificationsHelper(request)
    if notifications_helper.check_user_is_anonymous():
        return {}
    notifications_helper.process_notifications()
    return {'notifications': {
        'list': notifications_helper.messages,
        'unread_count': notifications_helper.unread_count}
    }
