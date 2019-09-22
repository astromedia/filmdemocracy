FROM python:3.6

ENV PYTHONUNBUFFERED 1

RUN pip install pip --upgrade
COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN apt-get update && apt-get -y install gettext

COPY scripts/start_website.sh ./

WORKDIR /code
