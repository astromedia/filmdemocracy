#!/bin/bash


#### SETTINGS ####

APPS_DIR='filmdemocracy'
declare -a WEB_APPS=("core" "registration" "democracy" "chat")


#######################
#### START WEBSITE ####
#######################

WORKDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

for WEB_APP in "${WEB_APPS[@]}"; do
  python manage.py makemigrations ${WEB_APP}
done

python manage.py migrate

cd ${APPS_DIR} || exit
django-admin compilemessages

cd ${WORKDIR}/.. || exit
python manage.py feed_db_with_films --test
python manage.py runserver 0.0.0.0:8000

exit 0
