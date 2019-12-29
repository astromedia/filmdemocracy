#!/bin/bash

#### SETTINGS ####

# Variables must be set as env variables


#### START SCRIPT ####

declare -a WEB_APPS=("core" "registration" "democracy" "chat")

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"

cd "${MAIN_DIR}" || exit 1

for WEB_APP in "${WEB_APPS[@]}"; do
  echo "python manage.py makemigrations ${WEB_APP}"
  python manage.py makemigrations ${WEB_APP}
done

echo "python manage.py migrate"
python manage.py migrate

echo "Done"

exit 0
