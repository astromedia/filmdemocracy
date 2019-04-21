#!/bin/bash


#### SETTINGS ####

APPS_DIR=filmdemocracy
declare -a WEB_APPS=("registration" "democracy")


#######################
#### START WEBSITE ####
#######################


for WEB_APP in ${WEB_APPS[@]}; do
  python manage.py makemigrations ${WEB_APP}
done

python manage.py migrate

cd ${APPS_DIR}
django-admin compilemessages
cd ..

python manage.py runserver 0.0.0.0:8000

exit 0
