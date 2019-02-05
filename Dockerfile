FROM python:3.6

ENV PYTHONUNBUFFERED 1
COPY requirements.txt start_db.sh ./
RUN pip install -r requirements.txt
WORKDIR /code
