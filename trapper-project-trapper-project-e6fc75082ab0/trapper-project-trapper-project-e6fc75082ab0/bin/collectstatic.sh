#!/bin/bash

###############################################################
#
# Run collectstatic -l
#
###############################################################

NAME="trapper - collectstatic"

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"

echo "Starting $NAME as `whoami`"

cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

exec python manage.py collectstatic -l --noinput
