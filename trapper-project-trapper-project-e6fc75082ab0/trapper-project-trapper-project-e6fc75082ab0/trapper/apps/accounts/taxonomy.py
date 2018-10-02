# -*- coding: utf-8 -*-
"""
Module containing various values used with accounts application
"""

from celery import states

from trapper.apps.common.taxonomy import BaseTaxonomy


class StateSettings(BaseTaxonomy):
    STOPPABLE = [states.PENDING, states.RECEIVED]

    STATE_MAP = {
        states.PENDING: {
            'css': u'default', 'icon': u'fa-clock-o',
            'title': 'Task status: PENDING',
            'action_detail': True,
            'action_stop': True,
        },
        states.RECEIVED: {
            'css': u'default', 'icon': u'fa-clock-o',
            'title': 'Task status: RECEIVED',
            'action_detail': True,
            'action_stop': True,
        },
        states.STARTED: {
            'css': u'primary', 'icon': u'fa-spin fa-refresh',
            'title': 'Task status: STARTED',
            'action_detail': True,
            'action_stop': True,
        },
        states.SUCCESS: {
            'css': u'success', 'icon': u'fa-check',
            'title': 'Task status: SUCCESS',
            'action_detail': True,
            'action_stop': False,
        },
        states.FAILURE: {
            'css': u'danger', 'icon': u'fa-close',
            'title': 'Task status: FAILURE',
            'action_detail': True,
            'action_stop': False,
        },
        states.REVOKED: {
            'css': u'warning', 'icon': u'fa-exclamation',
            'title': 'Task status: REVOKED',
            'action_detail': True,
            'action_stop': False,
        },
        states.RETRY: {
            'css': u'warning', 'icon': u'fa-exclamation',
            'title': 'Task status: RETRY',
            'action_detail': True,
            'action_stop': False,
        },
        states.IGNORED: {
            'css': u'warning', 'icon': u'fa-exclamation',
            'title': 'Task status: IGNORED',
            'action_detail': True,
            'action_stop': False,
        },
        states.REJECTED: {
            'css': u'danger', 'icon': u'fa-close',
            'title': 'Task status: REJECTED',
            'action_detail': True,
            'action_stop': False,
        },
    }


class ExternalStorageSettings(BaseTaxonomy):
    COLLECTIONS = 'collections'
    RESOURCES = 'resources'
    LOCATIONS = 'locations'
    DATA_PACKAGES = 'data_packages'

    DIRS = [
        COLLECTIONS, RESOURCES,
        LOCATIONS, DATA_PACKAGES
    ]


class PackageType(BaseTaxonomy):
    """Data package types handled by :class:`accounts.UserDataPackage`"""
    MEDIA_FILES = 'M'
    CLASSIFICATION_RESULTS = 'C'

    CHOICES = (
        (MEDIA_FILES, 'Media files'),
        (CLASSIFICATION_RESULTS, 'Classification results'),
    )
