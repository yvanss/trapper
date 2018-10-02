#!/bin/bash

###############################################################
#
# Prepare database for project
#
###############################################################

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"

cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

cd "${PROJECT_DIR}"

./manage.sh clean_pyc

python manage.py migrate
python manage.py migrate --list

#python manage.py load_example_data --force-reset
python manage.py loaddata trapper/apps/variables/fixtures/default_variables.json
python manage.py loaddata trapper/apps/common/fixtures/default_tiles.json
