#!/bin/bash

###############################################################
#
# Remove .pyc files from project
#
###############################################################

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")

find "${PROJECT_DIR}" -name "*.pyc" -exec rm -rf {} \;
