#!/bin/bash


#### SETTINGS ####

APPS_DIR='filmdemocracy'
declare -a WEB_APPS=("core" "registration" "democracy" "chat")


#######################
#### START WEBSITE ####
#######################

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR=${SCRIPTS_DIR}/..

cd ${MAIN_DIR} || exit

for WEB_APP in "${WEB_APPS[@]}"; do
  python manage.py makemigrations ${WEB_APP}
done

echo "python manage.py migrate"
python manage.py migrate

cd ${APPS_DIR} || exit

echo "django-admin compilemessages"
django-admin compilemessages

cd ${MAIN_DIR} || exit

if [ ${STORAGE_ENV} = "cloud" ]; then
#  gsutil mb gs://filmdemocracy-static-${VERSION_ENV}
#  gsutil defacl set public-read gs://filmdemocracy-static-${VERSION_ENV}
#  gsutil cors set gs-bucket-cors-config.json gs://filmdemocracy-static-${VERSION_ENV}
#  gsutil mb gs://filmdemocracy-media-${VERSION_ENV}
#  gsutil defacl set public-read gs://filmdemocracy-media-${VERSION_ENV}
#  gsutil cors set gs-bucket-cors-config.json gs://filmdemocracy-media-${VERSION_ENV}
  echo "python manage.py collectstatic --clear --noinput"
  python manage.py collectstatic --clear --noinput
  echo "python manage.py upload_static_files_to_gcs"
  python manage.py upload_static_files_to_gcs
fi

#python manage.py feed_db_with_films --test
#python manage.py create_mock_db
#python manage.py runserver 0.0.0.0:${WEB_APP_PORT}

exit 0
