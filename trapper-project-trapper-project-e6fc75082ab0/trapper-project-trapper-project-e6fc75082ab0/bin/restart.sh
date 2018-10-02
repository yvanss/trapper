#!/bin/bash

###############################################################
#
# send -HUP to all processess related to project
#
###############################################################

PROJECT_NAME='trapper'

ps aux | grep "gunicorn" | grep "${PROJECT_NAME}" | awk '{ print $2 }' | xargs kill -HUP
ps aux | grep "celery" | grep "${PROJECT_NAME}" | awk '{ print $2 }' | xargs kill -HUP
