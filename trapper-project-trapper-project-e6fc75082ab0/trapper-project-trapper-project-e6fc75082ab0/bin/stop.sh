#!/bin/bash

###############################################################
#
# Stop all processess related to project
#
###############################################################

PROJECT_NAME='trapper'

ps aux | grep "gunicorn" | grep "${PROJECT_NAME}" | awk '{ print $2 }' | xargs kill
ps aux | grep "celery" | grep "${PROJECT_NAME}" | awk '{ print $2 }' | xargs kill
