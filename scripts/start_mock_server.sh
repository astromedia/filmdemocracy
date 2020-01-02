#!/bin/bash

#### SETTINGS ####


#### START WEBSITE ####

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"

cd "${MAIN_DIR}" || exit 1

sleep 30

bash "${SCRIPTS_DIR}/migrate.sh"
bash "${SCRIPTS_DIR}/compile_messages.sh"

python manage.py feed_db_with_test_films --test
python manage.py create_mock_db
python manage.py runserver 0.0.0.0:8080

exit 0
