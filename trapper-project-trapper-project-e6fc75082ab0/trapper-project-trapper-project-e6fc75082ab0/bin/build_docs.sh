#!/bin/bash

###############################################################
#
# Build latest version of documentation
#
###############################################################

NAME="trapper - dev server"

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")
ENV_DIR="${PROJECT_DIR}/env/"
DOC_DIR="${PROJECT_DIR}/docs/"


echo "Starting $NAME as `whoami`"

cd "${PROJECT_DIR}"

if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

cd "${DOC_DIR}"
make html
