FROM python:3.6

ENV PYTHONUNBUFFERED 1
COPY requirements.txt start_db.sh ./
RUN pip install -r requirements.txt
RUN apt-get update && apt-get -y install gettext
WORKDIR /code
