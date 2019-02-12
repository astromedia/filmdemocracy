#!/bin/bash

python manage.py makemigrations registration
python manage.py makemigrations democracy
python manage.py sqlmigrate registration 0001
python manage.py sqlmigrate democracy 0001
python manage.py migrate

cd filmdemocracy
django-admin compilemessages
cd ..

python manage.py runserver 0.0.0.0:8000
