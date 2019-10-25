import uuid

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.utils.decorators import method_decorator

from filmdemocracy.core.models import Notification
from filmdemocracy.core.utils import NotificationsHelper


@login_required
def notification_dispatcher(request, ntf_type, ntf_club_id, ntf_object_id):
    notifications_helper = NotificationsHelper()
    url = notifications_helper.get_dispatch_url(ntf_type, ntf_club_id, ntf_object_id)
    ntf_ids_string = request.POST.get('ntf_ids')
    for ntf_id in ntf_ids_string.split('_'):
        ntf = get_object_or_404(Notification, id=uuid.UUID(ntf_id).hex, recipient=request.user)
        ntf.read = True
        ntf.save()
    return HttpResponseRedirect(url)


@login_required
def notification_cleaner(request):
    notifications_helper = NotificationsHelper(request)
    notifications = notifications_helper.get_user_notifications()
    for ntf in notifications:
        ntf.read = True
        ntf.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class HomeView(generic.TemplateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['user_clubs'] = self.request.user.club_set.all()
        return context


@method_decorator(login_required, name='dispatch')
class TourView(generic.TemplateView):
    pass


class TermsAndConditionsView(generic.TemplateView):
    pass
