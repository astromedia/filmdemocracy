#!/bin/bash


## FilmDemocracy database backup:

## Step 1: Make sure database service is running
## Step 2: Run script ("bash create_db_backup.sh")


#### SETTINGS ####

DB_SERVICE=filmdemocracy_db_1

WORKDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR=${WORKDIR}/..
LOCAL_DIR=${MAIN_DIR}/local
BACKUP_DIR=${LOCAL_DIR}/backups_db
MEDIA_DIR=${LOCAL_DIR}/db_media


########################
#### PERFORM BACKUP ####
########################

cd ${WORKDIR} || exit
source ./common_utils.sh

BACKUP_DIR=$(realpath ${BACKUP_DIR})
MEDIA_DIR=$(realpath ${MEDIA_DIR})
TIMESTAMP=$(date +%Y%m%d)
FINAL_BACKUP_DIR=${BACKUP_DIR}/${TIMESTAMP}

# Check media dir exists
if [[ ! -d "${MEDIA_DIR}" ]]; then
	echo -e "***ERROR: Media directory not found: ${MEDIA_DIR}" 1>&2
	exit 1
fi

# Create backup dir
if [[ ! -d "${BACKUP_DIR}" ]]; then
	echo -e "Creating backup directory in ${BACKUP_DIR}..."
	mkdir ${BACKUP_DIR}
fi

# Check if today's backup already exits
if [[ -d "${FINAL_BACKUP_DIR}" ]]; then
  if ask "Today's backup has already been created. Overwrite?" Y; then
    echo "Creating temporary backup of already existant backup..."
    mv ${FINAL_BACKUP_DIR} ${FINAL_BACKUP_DIR}.bak
    OLD_BACKUP_EXISTS=true
  else
    echo "Aborting backup creation"
    exit 1
  fi
else
  OLD_BACKUP_EXISTS=false
fi

function restore_old_backup_if_exists {
  if [ $1 = true ]; then
    echo -e "\nRestoring old backup..."
    mv ${FINAL_BACKUP_DIR}.bak ${FINAL_BACKUP_DIR}
  fi
}

function delete_old_backup_if_exists {
  if [ $1 = true ]; then
    echo -e "\nDeleting old backup..."
    rm -rf ${FINAL_BACKUP_DIR}.bak
  fi
}

echo -e "Creating backup directory in ${FINAL_BACKUP_DIR}..."

if ! mkdir -p ${FINAL_BACKUP_DIR}; then
  echo "***ERROR: Cannot create backup directory in ${FINAL_BACKUP_DIR}" 1>&2
  exit 1
fi

echo -e "\nPerforming backup..."

echo -e "\nPerforming postgres database backup..."
echo "docker exec -t ${DB_SERVICE} pg_dumpall -c -U postgres | gzip > ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz"
if ! docker exec -t ${DB_SERVICE} pg_dumpall -c -U postgres | gzip > ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz.in_progress; then
  echo "***ERROR: Failed to produce postgres backup" 1>&2
  rm -rf ${FINAL_BACKUP_DIR}
  restore_old_backup_if_exists ${OLD_BACKUP_EXISTS}
  exit 1
else
  mv ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz.in_progress ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz
  echo -e "\nPerforming media files backup..."
  echo "tar -cvzf ${FINAL_BACKUP_DIR}/db_media_backup.tar.gz -C ${MEDIA_DIR} ."
  if ! tar -cvzf ${FINAL_BACKUP_DIR}/db_media_backup.tar.gz -C ${MEDIA_DIR} .; then
    echo "***ERROR: Failed to backup media files" 1>&2
    rm -rf ${FINAL_BACKUP_DIR}
    restore_old_backup_if_exists ${OLD_BACKUP_EXISTS}
    exit 1
  else
    delete_old_backup_if_exists ${OLD_BACKUP_EXISTS}
    echo -e "\nBackup completed"
  fi

fi

exit 0
