#!/bin/bash


#### SETTINGS ####

APPS_DIR='filmdemocracy'
LOGOS_DIR='local/db_media/club_logos'
PROFILE_IMAGES_DIR='local/db_media/user_profile_images'
declare -a WEB_APPS=("core" "registration" "democracy" "chat")


####################
# CLEAN MIGRATIONS #
####################

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR=${SCRIPTS_DIR}/..

cd ${MAIN_DIR} || exit

for WEB_APP in "${WEB_APPS[@]}"; do
  sudo rm -rf ./${APPS_DIR}/${WEB_APP}/migrations
done

sudo rm -rf ./${LOGOS_DIR}/*
sudo rm -rf ./${PROFILE_IMAGES_DIR}/*

echo 'Done'

exit 0
