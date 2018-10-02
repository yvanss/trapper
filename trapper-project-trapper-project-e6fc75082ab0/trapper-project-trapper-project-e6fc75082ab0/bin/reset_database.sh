#!/bin/bash

###############################################################
#
# Start fresh with database
#
###############################################################

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=$(readlink -f "${SCRIPT_DIR}/..")

cd "${PROJECT_DIR}"

psql -h localhost -U trapper template1 < sql/reset_database.sql

./manage.sh setup_database
