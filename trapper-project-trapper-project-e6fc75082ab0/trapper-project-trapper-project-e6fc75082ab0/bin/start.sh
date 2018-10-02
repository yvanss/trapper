#!/bin/bash

###############################################################
#
# Start gunicorn server with project in virtualenv
#
###############################################################

NAME="trapper - main"

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"
LOGS_FILE="${PROJECT_DIR}/logs/gunicorn.log"
SOCKET_FILE="${PROJECT_DIR}/run/gunnicorn.sock"

NUM_WORKERS=3
DJANGO_SETTINGS_MODULE=trapper.settings
DJANGO_WSGI_MODULE=trapper.wsgi

LOG_LEVEL='info'

# Uncomment and adjust if user/group needs to be specified
#USER=trapper
#GROUP=trapper

echo "Starting $NAME as `whoami`"
 
# Activate the virtual environment
cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}
export PYTHONPATH=${PROJECT_DIR}:${PYTHONPATH}
 
# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec gunicorn "${DJANGO_WSGI_MODULE}:application" \
  --name "${NAME}" \
  --workers "${NUM_WORKERS}" \
  --bind="unix:${SOCKET_FILE}" \
  --log-level="${LOG_LEVEL}" \
  --log-file="${LOGS_FILE}" \
  --limit-request-line=0
#  --user="${USER}" --group="${GROUP}"
