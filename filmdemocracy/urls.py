"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from filmdemocracy import views


urlpatterns = [
    path('', views.redirect_to_home),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    url(r'^markdownx/', include('markdownx.urls')),
]

urlpatterns += i18n_patterns(
    path(
        '',
        include('filmdemocracy.democracy.urls')
    ),
    path(
        'registration/',
        include('filmdemocracy.registration.urls')
    ),
    path(
        '',
        views.HomeView.as_view(template_name='global/home.html'),
        name='home'
    ),
    path(
        'terms_and_conditions/',
        views.TermsAndConditionsView.as_view(template_name='global/terms_and_conditions.html'),
        name='terms_and_conditions'
    ),
    path(
        'notification_dispatcher/<str:ntf_type>/<str:ntf_club_id>/<str:ntf_object_id>/',
        views.notification_dispatcher,
        name='notification_dispatcher'
    ),
    path(
        'notification_cleaner/',
        views.notification_cleaner,
        name='notification_cleaner'
    ),
)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
