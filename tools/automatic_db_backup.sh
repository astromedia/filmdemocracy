#!/bin/bash


## FilmDemocracy automatic database backup:

## Step 1: Make sure database service is running
## Step 2: Run script ("bash automatic_db_backup.sh")


#### SETTINGS ####

DB_SERVICE=filmdemocracy_db_1

WORKDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR=${WORKDIR}/..
LOCAL_DIR=${MAIN_DIR}/local
BACKUP_DIR=${LOCAL_DIR}/db_backups
MEDIA_DIR=${LOCAL_DIR}/media

# Which day to take the weekly backup from (1-7 = Monday-Sunday)
DAY_OF_WEEK_TO_KEEP=6
 
# Number of days to keep daily backups
DAYS_TO_KEEP=7
 
# How many weeks to keep weekly backups
WEEKS_TO_KEEP=5


########################
#### PERFORM BACKUP ####
########################
 

BACKUP_DIR=$(realpath ${BACKUP_DIR})
MEDIA_DIR=$(realpath ${MEDIA_DIR})


function perform_backup()
{
	SUFFIX=$1
	FINAL_BACKUP_DIR=${BACKUP_DIR}/"`date +\%Y-\%m-\%d`-${SUFFIX}"
 
 	if [[ -d "${FINAL_BACKUP_DIR}" ]]; then
  		
  		echo -e "Today's backup has already been created! Skipping backup creation..."
	
	else
	
		echo -e "Creating $1 backup directory in ${FINAL_BACKUP_DIR}"

		if ! mkdir -p ${FINAL_BACKUP_DIR}; then
			echo "[!!!ERROR!!!] Cannot create backup directory in ${FINAL_BACKUP_DIR}" 1>&2
			exit 1;
		fi;

		echo -e "\nPerforming $1 backup...\n"

		echo "docker exec -t ${DB_SERVICE} pg_dumpall -c -U postgres | gzip > ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz"
	    if ! docker exec -t ${DB_SERVICE} pg_dumpall -c -U postgres | gzip > ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz.in_progress; then
			echo "[!!!ERROR!!!] Failed to produce postgres backup" 1>&2
			rm -rf ${FINAL_BACKUP_DIR}
	    else
	    	echo -e "Postgres database backup completed\n"
			mv ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz.in_progress ${FINAL_BACKUP_DIR}/pg_db_backup.sql.gz
	    	echo "tar -cvzf ${FINAL_BACKUP_DIR}/media_backup.tar.gz -C ${MEDIA_DIR} ."
	    	if ! tar -cvzf ${FINAL_BACKUP_DIR}/media_backup.tar.gz -C ${MEDIA_DIR} .; then
				echo "[!!!ERROR!!!] Failed to backup media files" 1>&2
				rm -rf ${FINAL_BACKUP_DIR}
		    else
		    	echo -e "Media backup completed\n"
				echo -e "Backup completed!"
		    fi

	    fi

	fi
}


# CHECK MEDIA DIR EXISTS

if [[ ! -d "${MEDIA_DIR}" ]]; then
	echo -e "[!!!ERROR!!!] Media directory ${MEDIA_DIR} not found!" 1>&2
	exit 1
fi

# CREATE BACKUP DIR

if [[ ! -d "${BACKUP_DIR}" ]]; then
	echo -e "Creating backup directory in ${BACKUP_DIR}"
	mkdir ${BACKUP_DIR}
fi

# MONTHLY BACKUPS
 
DAY_OF_MONTH=`date +%d`
 
if [[ ${DAY_OF_MONTH} -eq 1 ]];
then
	# Delete all expired monthly directories
	find ${BACKUP_DIR} -maxdepth 1 -name "*-monthly" -exec rm -rf '{}' ';'
 
	perform_backup "monthly"
 
	exit 0;
fi
 
# WEEKLY BACKUPS
 
DAY_OF_WEEK=`date +%u` # 1-7 (Monday-Sunday)
EXPIRED_DAYS=`expr $((($WEEKS_TO_KEEP * 7) + 1))`


if [ ${DAY_OF_WEEK} = ${DAY_OF_WEEK_TO_KEEP} ];
then
	# Delete all expired weekly directories
	find ${BACKUP_DIR} -maxdepth 1 -mtime +${EXPIRED_DAYS} -name "*-weekly" -exec rm -rf '{}' ';'
 
	perform_backup "weekly"
 
	exit 0;
fi
 
# DAILY BACKUPS
 
# Delete daily backups 7 days old or more
find ${BACKUP_DIR} -maxdepth 1 -mtime +${DAYS_TO_KEEP} -name "*-daily" -exec rm -rf '{}' ';'
 
perform_backup "daily"

exit 0
