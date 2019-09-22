#!/bin/bash


## FilmDemocracy database restoration steps:

## Step 1: cd to build context where docker-compose.yml file is located
## Step 2: docker-compose down (rm all running containers)
## Step 3: docker-compose up -d db (start db container in detached mode)
## Step 4: run restoration script (example: "bash restore_db_from_backup.sh 20190417")
## Step 5: docker-compose up (start all remaining services as normal and enjoy)


#### SETTINGS ####

DB_SERVICE=filmdemocracy_db_1

WORKDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR=${WORKDIR}/..
LOCAL_DIR=${MAIN_DIR}/local
BACKUP_DIR=${LOCAL_DIR}/backups_db
MEDIA_DIR=${LOCAL_DIR}/db_media


##########################
#### RESTORE DATABASE ####
##########################

cd ${WORKDIR} || exit
source ./common_utils.sh

BACKUP_DIR=$(realpath ${BACKUP_DIR})
MEDIA_DIR=$(realpath ${MEDIA_DIR})


if [[ $1 == "" ]]; then
	echo -e "USAGE: restore_db_from_backup.sh <date>"
	echo -e "\n<date> format: YYYYMMDD (example: 20190409)"
	exit 1
fi

# Check backup dir exists
if [ ! -d "${BACKUP_DIR}" ]; then
	echo -e "***ERROR: Base backup directory not found: ${BACKUP_DIR}" 1>&2
	exit 1
fi

RESTORE_DATE=$1
FINAL_BACKUP_DIR_PREFIX=${BACKUP_DIR}/${RESTORE_DATE}
FINAL_BACKUP_DIR=$(realpath ${FINAL_BACKUP_DIR_PREFIX})

# Check selected day backup dir exists
if [ ! -d "${FINAL_BACKUP_DIR}" ]; then
	echo "***ERROR: Backup directory not found: ${FINAL_BACKUP_DIR}" 1>&2
	exit 1
else
	echo -e "Backup directory found: ${FINAL_BACKUP_DIR}"
fi

# Check selected day backup files exist
if [ ! -f ${FINAL_BACKUP_DIR}/db_media_backup.tar.gz ]; then
    echo "***ERROR: Backup file not found: db_media_backup.tar.gz"  1>&2
	exit 1
else	
	echo "Media backup file found: ${FINAL_BACKUP_DIR}/db_media_backup.tar.gz"
fi

if [ ! -f ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz ]; then
    echo "***ERROR: Backup file not found: pg_db_backup.sql.gz"  1>&2
	exit 1
else
	echo -e "Postgres backup file found: ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz\n"
fi

# Restore database from backup files
if ask "Are you sure you want to continue?" Y; then
	echo -e "\nRestoring database from backup...\n"
else
  echo "Aborting database restoration"
  exit 1
fi

# Check if media dir exists
if [ -d "${MEDIA_DIR}" ]; then
	echo -e "A media directory already exists at: ${MEDIA_DIR}\n"
	if ask "Do you want to delete it and continue?" Y; then
		rm -rf ${MEDIA_DIR}
		mkdir ${MEDIA_DIR}
	else
		echo "Aborting database restoration"
		exit 1
	fi
else
	mkdir ${MEDIA_DIR}
fi

gunzip -k ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz

echo "cat ${FINAL_BACKUP_DIR}/pg_db_backup.sql | docker exec -i ${DB_SERVICE} psql -U postgres"
if ! cat ${FINAL_BACKUP_DIR}/pg_db_backup.sql | docker exec -i ${DB_SERVICE} psql -U postgres; then
	echo "***ERROR: Failed to restore postgres backup" 1>&2
else
	echo -e "\nPostgres database restoration completed\n"
	echo "tar -xzf ${FINAL_BACKUP_DIR}/db_media_backup.tar.gz -C ${MEDIA_DIR}"
	if ! tar -xzf ${FINAL_BACKUP_DIR}/db_media_backup.tar.gz -C ${MEDIA_DIR}; then
		echo "***ERROR: Failed to restore media files" 1>&2
    else
    	echo -e "\nMedia restoration completed\n"
		echo -e "\nRestoration completed"
    fi
fi

rm -f ${FINAL_BACKUP_DIR}/pg_db_backup.sql

exit 0
