#!/bin/bash

###############################################################
#
# Update project dependencies and database changes
#
###############################################################

NAME="trapper - update project"

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"

echo "Starting $NAME as `whoami`"

cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

pip install -e .
python manage.py migrate
