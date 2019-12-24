FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get -y install gettext

RUN pip install pip --upgrade
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . /code

ENV LOCAL_PORT 8080
ENV VERSION_ENV 'dev'
ENV DATABASE_ENV 'cloud'
ENV STATIC_ENV 'cloud'
ENV MEDIA_ENV 'cloud'

WORKDIR /code

CMD export DATABASE_ENV="cloudproxy" && python manage.py feed_db_with_films --cleandb --overwrite
#CMD ./scripts/make_messages.sh
#CMD ./scripts/compile_messages.sh
#CMD python manage.py runserver 0.0.0.0:${LOCAL_PORT}

#CMD ./scripts/start_mock_server.sh && python manage.py runserver 0.0.0.0:${LOCAL_PORT}
#CMD gunicorn -b :$PORT filmdemocracy.wsgi
