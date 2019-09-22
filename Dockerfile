FROM python:3.6

ENV PYTHONUNBUFFERED 1

COPY requirements.txt tools/start_website.sh ./
RUN pip install pip --upgrade
RUN pip install -r requirements.txt
RUN apt-get update && apt-get -y install gettext

WORKDIR /code
