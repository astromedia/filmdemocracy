#!/bin/bash

#### SETTINGS ####

APPS_DIR_NAME="filmdemocracy"
LOGOS_DIR="local/media/club_logos"
PROFILE_IMAGES_DIR="local/media/user_profile_images"
declare -a WEB_APPS=("core" "registration" "democracy")


#### CLEAN MIGRATIONS ####

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"
APPS_DIR="${MAIN_DIR}/${APPS_DIR_NAME}"

for WEB_APP in "${WEB_APPS[@]}"; do
  sudo rm -rf "${APPS_DIR}/${WEB_APP}/migrations"
done

sudo rm -rf "${MAIN_DIR}/${LOGOS_DIR}/*"
sudo rm -rf "${MAIN_DIR}/${PROFILE_IMAGES_DIR}/*"

#### CLEAN POSTGRESDB ####

docker volume rm $(docker volume ls -q)

echo "Done"

exit 0
