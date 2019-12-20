FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get -y install gettext

RUN pip install pip --upgrade
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . /code

ENV WEB_APP_PORT 8080
ENV VERSION_ENV 'dev'
ENV DATABASE_ENV 'cloudproxy'
ENV STATIC_ENV 'local'
ENV MEDIA_ENV 'cloud'
ENV GOOGLE_APPLICATION_CREDENTIALS '/code/secrets/storage-credentials.json'

WORKDIR /code

CMD python manage.py feed_db_with_films
#CMD ./scripts/prepare_website.sh
#CMD python manage.py runserver 0.0.0.0:${WEB_APP_PORT}
#CMD ./scripts/prepare_website.sh && python manage.py runserver 0.0.0.0:${WEB_APP_PORT}
#CMD gunicorn -b :$PORT filmdemocracy.wsgi
