#!/bin/bash

###############################################################
#
# Run project on 0.0.0.0:6700 in development mode
#
###############################################################

NAME="trapper - test"

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"

echo "Starting $NAME as `whoami`"

cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

exec python manage.py test $@ --settings=trapper.settings_test

