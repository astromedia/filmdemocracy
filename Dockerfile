FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get -y install gettext

RUN pip install pip --upgrade
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . /code

ENV PORT 8080

WORKDIR /code

# Commands to manage db films:
# CMD python manage.py feed_db_with_films --dryrun --verbose
# CMD python manage.py feed_db_with_films --overwrite --verbose
# CMD python manage.py feed_db_with_films --overwrite
# CMD python manage.py feed_db_with_films --reset

# Misc commands:
# CMD ./scripts/collect_and_upload_static.sh
# CMD ./scripts/make_migrations.sh
# CMD ./scripts/migrate.sh
# CMD ./scripts/make_messages.sh
# CMD ./scripts/compile_messages.sh
# CMD ./scripts/local_clean_start.sh

# Run server commands:
CMD ./scripts/start_mock_server.sh
# CMD python manage.py runserver 0.0.0.0:8080
# CMD gunicorn -b :$PORT filmdemocracy.wsgi