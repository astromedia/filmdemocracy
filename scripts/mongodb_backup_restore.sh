#!/bin/bash


DATE=$1


SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"
BACKUP_DIR=${MAIN_DIR}/local/data/mongodb/backups


if [ ! -f ${BACKUP_DIR}/dump_${DATE}.gz ]; then
    echo "Error: MongoDB backup file not found: ${BACKUP_DIR}/dump_${DATE}.gz"  1>&2
	exit 1
else	
	echo "MongoDB backup file found: ${BACKUP_DIR}/dump_${DATE}.gz"
fi


mongorestore --gzip --archive=${BACKUP_DIR}/dump_${DATE}.gz

exit 0
