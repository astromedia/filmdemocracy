#!/bin/bash

python manage.py makemigrations
python manage.py migrate

cd filmdemocracy
django-admin compilemessages
cd ..

python manage.py runserver 0.0.0.0:8000
