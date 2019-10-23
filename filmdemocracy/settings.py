"""
Django settings for filmdemocracy project.

Generated by 'django-admin startproject' using Django 2.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _

from filmdemocracy.secrets import SECRET_KEY, EMAIL_HOST_PASSWORD


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!

DEBUG = True

# TODO: This value is not safe for production usage. https://docs.djangoproject.com/en/1.11/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'filmdemocracy.core',
    'filmdemocracy.registration',
    'filmdemocracy.democracy',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'markdownx',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'filmdemocracy.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'filmdemocracy/core/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'filmdemocracy.core.context_processors.notifications',
            ],
        },
    },
]


WSGI_APPLICATION = 'filmdemocracy.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'HOST': 'db',
        'PORT': 5432,
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

# TODO: disable in production!!!
AUTH_PASSWORD_VALIDATORS = []

# TODO: uncomment in production!!!
# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LOCALE_PATHS = [os.path.join(BASE_DIR, 'filmdemocracy/locale')]

LANGUAGES = [
    ('en', _('English')),
    ('es', _('Spanish')),
]

LANGUAGE_CODE = 'en'

USE_I18N = True

USE_L10N = True

USE_TZ = True
TIME_ZONE = 'Europe/Madrid'  # TODO: use pytz


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'filmdemocracy/static/')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'filmdemocracy/core/static'),
]


# Login redirect

LOGIN_URL = '/registration/login/'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'


# Dev email backend

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'filmdemocracyweb'
# EMAIL_HOST_PASSWORD = 'gmail password'
DEFAULT_FROM_EMAIL = 'filmdemocracyweb@gmail.com'


# Using a custom user model when starting a project
# https://docs.djangoproject.com/en/2.1/topics/auth/customizing/#extending-the-existing-user-model

AUTH_USER_MODEL = 'registration.User'

MEDIA_URL = '/db_media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'local/db_media')


# Custom Bootstrap messages
# https://simpleisbetterthancomplex.com/tips/2016/09/06/django-tip-14-messages-framework.html

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}
