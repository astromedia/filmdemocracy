#!/bin/bash


## FilmDemocracy database restoration steps:

## Step 1: cd to build context where docker-compose.yml file is located
## Step 2: docker-compose down (rm all running containers)
## Step 3: docker-compose up -d db (start db container in detached mode)
## Step 4: run restoration script (example: "bash restore_db_from_backup.sh 2019-04-17")
## Step 5: docker-compose up (start all remaining services as normal and enjoy)


#### SETTINGS ####

DB_SERVICE=filmdemocracy_db_1
MAIN_DIR=..
LOCAL_DIR=${MAIN_DIR}/local
BACKUP_DIR=${LOCAL_DIR}/db_backups
MEDIA_DIR=${LOCAL_DIR}/media


##########################
#### RESTORE DATABASE ####
##########################


BACKUP_DIR=$(realpath ${BACKUP_DIR})
MEDIA_DIR=$(realpath ${MEDIA_DIR})


ask() {
    # https://gist.github.com/davejamesmiller/1965569
    local prompt default reply

    if [ "${2:-}" = "Y" ]; then
        prompt="Y/n"
        default=Y
    elif [ "${2:-}" = "N" ]; then
        prompt="y/N"
        default=N
    else
        prompt="y/n"
        default=
    fi

    while true; do

        # Ask the question (not using "read -p" as it uses stderr not stdout)
        echo -n "$1 [$prompt] "

        # Read the answer (use /dev/tty in case stdin is redirected from somewhere else)
        read reply </dev/tty

        # Default?
        if [ -z "$reply" ]; then
            reply=$default
        fi

        # Check if the reply is valid
        case "$reply" in
            Y*|y*) return 0 ;;
            N*|n*) return 1 ;;
        esac

    done
}


if [[ $1 == "" ]]; then
	echo -e "USAGE: restore_db_from_backup.sh <date>"
	echo -e "\n<date> format: YYYY-MM-DD (example: 2019-04-09)"
	exit 1
fi

# CHECK BACKUP DIR EXISTS

if [ ! -d "${BACKUP_DIR}" ]; then
	echo -e "[!!!ERROR!!!] Backup directory ${BACKUP_DIR} not found!" 1>&2
	exit 1
fi

RESTORE_DATE=$1
FINAL_BACKUP_DIR_PREFIX=${BACKUP_DIR}/${RESTORE_DATE}
FINAL_BACKUP_DIR=$(realpath $(find ${FINAL_BACKUP_DIR_PREFIX}* -type d))

# CHECK SELECTED DAY BACKUP DIR EXISTS

if [ ! -d "${FINAL_BACKUP_DIR}" ]; then
	echo "[!!!ERROR!!!] Backup directory not found!" 1>&2
	exit 1;
else
	echo -e "Backup directory found: ${FINAL_BACKUP_DIR}"
fi

# CHECK SELECTED DAY BACKUP FILES EXIST

if [ ! -f ${FINAL_BACKUP_DIR}/media_backup.tar.gz ]; then
    echo "[!!!ERROR!!!] Backup file not found: media_backup.tar.gz"  1>&2
	exit 1;	
else	
	echo "Media backup file found: ${FINAL_BACKUP_DIR}/media_backup.tar.gz"
fi

if [ ! -f ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz ]; then
    echo "[!!!ERROR!!!] Backup file not found: pg_db_backup.sql.gz"  1>&2
	exit 1;	
else
	echo -e "Postgres backup file found: ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz\n"
fi

# RESTORE DATABASE FROM BACKUP FILES

if ask "Are you sure you want to continue?" Y; then
	echo -e "\nRestoring database from backup...\n"
else
    echo "Aborting database restoration"
    exit 1
fi

# CHECK IF MEDIA DIR EXISTS

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
	echo "[!!!ERROR!!!] Failed to restore postgres backup" 1>&2
else
	echo -e "Postgres database restoration completed\n"
	echo "tar -xzf ${FINAL_BACKUP_DIR}/media_backup.tar.gz -C ${MEDIA_DIR}"
	if ! tar -xzf ${FINAL_BACKUP_DIR}/media_backup.tar.gz -C ${MEDIA_DIR}; then
		echo "[!!!ERROR!!!] Failed to restore media files" 1>&2
    else
    	echo -e "Media restoration completed\n"
		echo -e "Restoration completed!"
    fi
fi

rm -f ${FINAL_BACKUP_DIR}/pg_db_backup.sql

exit 0
