#!/bin/bash

BASE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
BIN_DIR="${BASE_DIR}/bin/"
ENV_DIR="${BASE_DIR}/env/"

# Each command should activate venv, but here we can make sure it's activated
# even if command doesn't activate it itself
if [ -d "${ENV_DIR}" ]
then
    . "${ENV_DIR}bin/activate"
fi

if [ "$#" -lt 1 ]
then
    echo "Usage: $0 <command> [options]"
    exit 1
fi

COMMAND="$1"
COMMAND_ARGS="${*:2}"
COMMAND_PATH="${BIN_DIR}${COMMAND}.sh"

if [ -f "${COMMAND_PATH}" ]
then
    "${COMMAND_PATH}" "${COMMAND_ARGS}"
else
    echo "Command $COMMAND not found in ${BIN_DIR}"
    exit 1
fi
