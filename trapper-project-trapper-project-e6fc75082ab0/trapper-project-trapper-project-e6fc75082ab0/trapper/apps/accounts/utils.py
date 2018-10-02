# -*- coding: utf-8 -*-
"""
Common functions related to user accounts
"""
import os

from django.conf import settings

from trapper.apps.accounts.taxonomy import ExternalStorageSettings


def get_pretty_username(user):
    """
    Display pretty version of username.
    If user has first and last name, then it will be used. Username is
    used as fallback
    :param user: :class:`auth.User` instance
    :return: prettified username version
    """
    if not user:
        return None

    if user.first_name and user.last_name:
        username = u"{first} {last}".format(
            first=user.first_name, last=user.last_name)
    else:
        username = user.username
    return username


def get_external_media_path(username, filename=None, subdir=None):
    """For given username get external media directory path.
    This is used as separated method because it's also used in other places
    without creating directory.

    :param username: name of user that will be used to get path
    :param filename: if given, then complete path to file will be used
    :param subdir: if given, extra subdirectory will be added after
        username. This can be used for grouping files inside user
        external media directory (i.e. collections, resources, locations etc)
    """

    params = [settings.EXTERNAL_MEDIA_ROOT, username]

    if subdir:
        params.append(subdir)

    if filename:
        params.append(filename)

    return os.path.join(*params)


def get_external_collections_path(username, filename=None):
    """For given username get external media path for storing collections.
    This is used as separated method because it's also used in other places
    without creating directory.

    :param username: name of user that will be used to get path
    :param filename: if given, then complete path to file will be used
    """
    return get_external_media_path(
        username=username,
        filename=filename,
        subdir=ExternalStorageSettings.COLLECTIONS
    )


def get_external_resources_path(username, filename=None):
    """For given username get external media path for storing resources.
    This is used as separated method because it's also used in other places
    without creating directory.

    :param username: name of user that will be used to get path
    :param filename: if given, then complete path to file will be used
    """
    return get_external_media_path(
        username=username,
        filename=filename,
        subdir=ExternalStorageSettings.RESOURCES
    )


def get_external_locations_path(username, filename=None):
    """For given username get external media path for storing locations
    This is used as separated method because it's also used in other places
    without creating directory.

    :param username: name of user that will be used to get path
    :param filename: if given, then complete path to file will be used
    """
    return get_external_media_path(
        username=username,
        filename=filename,
        subdir=ExternalStorageSettings.LOCATIONS
    )


def get_external_data_packages_path(username, filename=None):
    """For given username get external media path for storing data_packages
    This is used as separated method because it's also used in other places
    without creating directory.

    :param username: name of user that will be used to get path
    :param filename: if given, then complete path to file will be used
    """
    return get_external_media_path(
        username=username,
        filename=filename,
        subdir=ExternalStorageSettings.DATA_PACKAGES
    )


def create_external_media(username):
    """For given username, make sure that directory for storing external
    media is available"""

    user_path = get_external_media_path(username=username)
    paths = [
        user_path,
        os.path.join(
            user_path, ExternalStorageSettings.COLLECTIONS
        ),
        os.path.join(user_path, ExternalStorageSettings.RESOURCES),
        os.path.join(user_path, ExternalStorageSettings.LOCATIONS),
        os.path.join(user_path, ExternalStorageSettings.DATA_PACKAGES)
    ]

    for p in paths:
        if not os.path.exists(p):
            os.makedirs(p)
