#!/bin/bash

###############################################################
#
# Run flower for project in virtualenv
#
###############################################################

NAME="trapper - flower"

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"

PORT=6800
BROKER=amqp://guest:guest@localhost:5672//
BACKEND=amqp
LOG_LEVEL='info'

echo "Starting $NAME as `whoami`"

# Activate the virtual environment
cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

exec celery \
  -A trapper flower \
  --name "${NAME}" \
  --port="${PORT}" \
  --loglevel="${LOG_LEVEL}" \
  --broker="${BROKER}" \
  --backend="${BACKEND}"

