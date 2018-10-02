#!/bin/bash

###############################################################
#
# Run celery beat for project in virtualenv
#
###############################################################

NAME="trapper - celery_beat"

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"

LOG_LEVEL='info'

echo "Starting $NAME as `whoami`"

cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi


exec celery \
  -A trapper beat \
  --loglevel="${LOG_LEVEL}" \

