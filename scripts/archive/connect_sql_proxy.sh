#!/bin/bash

#### SETTINGS ####

export VERSION_ENV="dev"


#### START SCRIPT ####

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"
export GOOGLE_APPLICATION_CREDENTIALS="${MAIN_DIR}/secrets/cloudsql-credentials.json"

cd "${MAIN_DIR}" || exit 1

./cloud_sql_proxy -instances="smart-grin-262119:europe-west1:filmdemocracy-${VERSION_ENV}"=tcp:0.0.0.0:5432

echo "Done"

exit 0
