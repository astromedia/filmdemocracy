FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get -y install gettext

RUN pip install pip --upgrade
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . /code

ENV VERSION_ENV 'dev'

#ENV DATABASE_ENV 'local'
ENV DATABASE_ENV 'sqlproxy'
#ENV DATABASE_ENV 'cloud'

ENV STATIC_ENV 'local'
#ENV STATIC_ENV 'cloud'

#ENV MEDIA_ENV 'local'
ENV MEDIA_ENV 'cloud'

ENV GOOGLE_APPLICATION_CREDENTIALS '/code/secrets/storage-credentials.json'

WORKDIR /code

# Commands to manage films in db:
#CMD python manage.py manage_films_db --updatedb
#CMD python manage.py manage_films_db --updatedb --overwrite
#CMD python manage.py manage_films_db --updatedb --cleandb
#CMD python manage.py manage_films_db --updatedb --cleandb --overwrite
#CMD python manage.py manage_films_db --updatedb --onlycleandb
#CMD python manage.py manage_films_db --dryrun

# Misc commands:
#CMD ./scripts/collect_and_upload_static.sh
#CMD ./scripts/perform_migrations.sh
#CMD ./scripts/make_messages.sh
#CMD ./scripts/compile_messages.sh
#CMD ./scripts/local_clean_start.sh
#CMD ./scripts/start_mock_server.sh

# Run server commands:
CMD python manage.py runserver 0.0.0.0:8080
#CMD gunicorn -b :$PORT filmdemocracy.wsgi
