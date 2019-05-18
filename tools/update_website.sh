#!/bin/bash


## FilmDemocracy auto-update script:

## Step 1: Make sure both database and web services are running
## Step 2: Run update script, force update with "--force" flag (example: "bash update_website.sh --force")


#### SETTINGS ####

WORKDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MAIN_DIR=${WORKDIR}/..

DB_SERVICE=filmdemocracy_db_1
WEB_SERVICE=filmdemocracy_web_1
APPS_DIR=filmdemocracy
declare -a WEB_APPS=("registration" "democracy")


########################
#### UPDATE WEBSITE ####
########################


ask() {
    # https://gist.github.com/davejamesmiller/1965569
    local prompt default reply

    if [[ "${2:-}" = "Y" ]]; then
        prompt="Y/n"
        default=Y
    elif [[ "${2:-}" = "N" ]]; then
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
        if [[ -z "$reply" ]]; then
            reply=$default
        fi

        # Check if the reply is valid
        case "$reply" in
            Y*|y*) return 0 ;;
            N*|n*) return 1 ;;
        esac

    done
}


function update_website()
{
	# GIT PULL

	echo -e "\nPulling code from GitHub..."
	git pull

	# MAKE MIGRATIONS

	echo -e "\nPerforming migrations..."
	for WEB_APP in ${WEB_APPS[@]}; do
		echo "docker exec ${WEB_SERVICE} python manage.py makemigrations ${WEB_APP}"
		docker exec ${WEB_SERVICE} python manage.py makemigrations ${WEB_APP}
	done
	echo "docker exec ${WEB_SERVICE} python manage.py migrate"
	docker exec ${WEB_SERVICE} python manage.py migrate
	
	# COMPILE MESSAGES

	echo -e "\nCompiling messages..."
	echo "docker exec ${WEB_SERVICE} bash -c 'cd ${APPS_DIR} && django-admin compilemessages'"
	docker exec ${WEB_SERVICE} bash -c "cd ${APPS_DIR} && django-admin compilemessages"

	echo -e "\nDone updating!"
}


cd MAIN_DIR

# FETCH CODE

echo -e "\nFetching code from github..."
git remote update

UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")

# TEST IF UPDATE NEEDED

if [[ $1 == '--force' ]]; then
    echo -e "\nStarting update"
    update_website
else
    if [[ ${LOCAL} = ${REMOTE} ]]; then
        echo -e "\nCode is up-to-date, no need to update"
        
    else
    	echo -e "\nCode in origin/master is ahead, starting update"
    	update_website
    fi
fi

exit 0
