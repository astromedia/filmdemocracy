#!/bin/bash


DB_NAME='filmdemocracy'


SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR="$( cd "$( dirname "${SCRIPTS_DIR}" )" >/dev/null 2>&1 && pwd )"
BACKUP_DIR=${MAIN_DIR}/local/data/mongodb/backups


# check backup dir exists
if [[ ! -d "${BACKUP_DIR}" ]]; then
	echo -e "***ERROR: backup directory not found: ${BACKUP_DIR}" 1>&2
	exit 1
fi


mongodump --db ${DB_NAME} --gzip --archive > ${BACKUP_DIR}/dump_`date "+%Y%m%d"`.gz

exit 0
