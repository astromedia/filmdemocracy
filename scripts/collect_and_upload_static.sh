#!/bin/bash

#### SETTINGS ####

APPS_DIR_NAME="filmdemocracy"
export VERSION_ENV="dev"


#### START WEBSITE ####

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"
APPS_DIR="${MAIN_DIR}/${APPS_DIR_NAME}"

cd "${MAIN_DIR}" || exit 1

export STATIC_ENV="cloud"
export MEDIA_ENV="cloud"
export GOOGLE_APPLICATION_CREDENTIALS="${MAIN_DIR}/secrets/storage-credentials.json"

#gsutil mb gs://filmdemocracy-static-${VERSION_ENV}
#gsutil defacl set public-read gs://filmdemocracy-static-${VERSION_ENV}
#gsutil cors set gs-bucket-cors-config.json gs://filmdemocracy-static-${VERSION_ENV}

#gsutil mb gs://filmdemocracy-media-${VERSION_ENV}
#gsutil defacl set public-read gs://filmdemocracy-media-${VERSION_ENV}
#gsutil cors set gs-bucket-cors-config.json gs://filmdemocracy-media-${VERSION_ENV}

echo "sudo rm -rf ${APPS_DIR}/static"
sudo rm -rf "${APPS_DIR}/static"

echo "python manage.py collectstatic"
python manage.py collectstatic

echo "python manage.py upload_static_files_to_gcs"
python manage.py upload_static_files_to_gcs

echo "Done"

exit 0
