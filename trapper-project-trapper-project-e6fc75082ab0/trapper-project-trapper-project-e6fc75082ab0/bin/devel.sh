#!/bin/bash

###############################################################
#
# Build venv + download all necesary packages.
#
###############################################################

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")

ENV_DIR='env'
BIN_DIR='bin'
VIRTUALENV=`which virtualenv`
PYTHON=`which python2.7`

cd "${PROJECT_DIR}"

if [ ! -d "$BIN_DIR" ]
then
    mkdir "$BIN_DIR"
fi

if [ ! -d "$ENV_DIR" ]
then
    "${VIRTUALENV}" -p "${PYTHON}" --no-site-packages "$ENV_DIR"
fi

. "$ENV_DIR"/bin/activate
pip install --ignore-installed -e .

# Install other apps that are not available from pip
pip install git+https://github.com/slav0nic/djangobb.git
