#!/bin/bash


#### SETTINGS ####

APPS_DIR='filmdemocracy'
declare -a WEB_APPS=("registration" "democracy")


####################
# CLEAN MIGRATIONS #
####################

WORKDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR=${WORKDIR}/..

cd ${MAIN_DIR} || exit

for WEB_APP in "${WEB_APPS[@]}"; do
  sudo rm -rf ./${APPS_DIR}/${WEB_APP}/migrations
done

echo 'Done'

exit 0
