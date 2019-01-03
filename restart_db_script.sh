#!/bin/bash

PROJECT_DIR=$(pwd)

rm $PROJECT_DIR/local/db.sqlite3
rm -rf $PROJECT_DIR/local/media
rm -rf $PROJECT_DIR/filmdemocracy/democracy/migrations
rm -rf $PROJECT_DIR/filmdemocracy/registration/migrations
rm -rf $PROJECT_DIR/filmdemocracy/socialclub/migrations
python manage.py makemigrations democracy
python manage.py makemigrations registration
python manage.py makemigrations socialclub
python manage.py sqlmigrate democracy 0001
python manage.py sqlmigrate registration 0001
python manage.py sqlmigrate socialclub 0001
python manage.py migrate

python manage.py shell < create_mock_db.py

exit 0
