#!/bin/bash

#### SETTINGS ####

APPS_DIR_NAME='filmdemocracy'


#### MAKE MESSAGES ####

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"
APPS_DIR="${MAIN_DIR}/${APPS_DIR_NAME}"

cd "${APPS_DIR}" || exit 1

echo "django-admin makemessages -l es"
django-admin makemessages -l es

exit 0
