# -*- coding: utf-8 -*-
"""
Celery configuration requires that all tasks that should be available for
asynchronous processing should be created in `tasks.py` file

This module contains minimal logic required to run celery task and
notify about results, classess and functions that actually do work
(i.e. creating thumbnails, processing uploaded collections) are defined
in other modules
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import os
import zipfile
import datetime
from celery import shared_task

from django.conf import settings
from django.utils.timezone import now

from trapper.apps.storage.thumbnailer import (
    Thumbnailer, ThumbnailerException
)
from trapper.apps.storage.collection_upload import (
    CollectionProcessor, CollectionProcessorException
)
from trapper.apps.storage.taxonomy import ResourceType
from trapper.apps.messaging.models import Message
from trapper.apps.accounts.utils import (
    get_external_data_packages_path, create_external_media
)
from trapper.apps.accounts.models import UserDataPackage
from trapper.apps.accounts.taxonomy import PackageType, ExternalStorageSettings


@shared_task
def celery_update_thumbnails(resources):
    """
    Celery task that create thumbnails for a list of images/videos

    :param resources: list of storage.Resource model instances
    """
    for resource in resources:
        if resource.resource_type in ResourceType.THUMBNAIL_TYPES:
            try:
                Thumbnailer(resource=resource).create()
            except ThumbnailerException:
                continue

@shared_task
def celery_process_collection_upload(
        definition_file, archive_file, owner
):
    """
    Celery task that creates collections using provided (uploaded) 
    definition (YAML) and data (ZIP archive) files.

    :param definition_file: a definition file (YAML)
    :param archive_file: a data file (ZIP archive) or a path to already 
    uploaded archive 
    :param owner: a user that will be an owner of new collection
    """
    start = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S`')

    message_success = (
        '<p>Collections in the data package <strong>{archive_file}</strong> that you '
        'have uploaded at <strong>{start}</strong> have been successfully processed at '
        '<strong>{end}</strong>.</p>'
    )
    message_success_errors = (
        'List of objects that could not be processed: <ul>{errors}</ul>'
    )
    message_failure = (
        '<p>Collections in the data package that you '
        'have uploaded at <strong>{start}</strong> could not be processed due to '
        'errors:<p> {errors}'
    )

    try:
        processor = CollectionProcessor(
            definition_file=definition_file,
            archive_file=archive_file,
            owner=owner
        )
        processor.create()
    except CollectionProcessorException as error:
        end = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S`')
        Message.objects.create(
            subject='Collection upload failed',
            text=message_failure.format(
                start=start,
                errors=error.args[0]
            ),
            user_from=owner,
            user_to=owner,
            date_sent=end
        )
    else:
        end = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S`')
        errors = []
        for col_name in processor.errors.keys():
            collection = processor.collections_processed[col_name]
            errors.append(u"<li>{name}<ul>".format(name=col_name))
            free_resources = collection.pop('free_resources', None)
            for dep_name in collection.keys():
                deployment = collection[dep_name]
                errors.append(u"<li>{name}<ul>".format(name=dep_name))
                for resource in deployment:
                    errors.append(
                        u"<li>{name}: {error}</li>".format(
                            name=resource[0], error=resource[1]
                        )
                    )
                errors.append(u'</ul></li>')
            errors.append(u'</ul></li>')

        archive_name = os.path.basename(
            processor.archive.filename
        )

        message_success = message_success.format(
            start=start, end=end,
            archive_file=archive_name
        )
        if errors:
            message_success += message_success_errors.format(
                errors="\n".join(errors)
            )
        Message.objects.create(
            subject=u"Collections ({archive_file}) upload finished successfully".format(
                archive_file=archive_name
            ),
            text=message_success,
            user_from=owner,
            user_to=owner,
            date_sent=end
        )

        return message_success


@shared_task
def celery_create_media_package(resources, user, package_name, metadata=False):
    """
    Celery task that creates a data package (archive) from selected
    resources.

    :param resources: queryset of storage.Resource model
    """

    USE_7ZIP = getattr(settings, 'USE_7ZIP', False)
    timestamp = now()
    if package_name:
        package_name = '.'.join([package_name, 'zip'])
    package_name =  package_name or "media_{0}.zip".format(
        timestamp.strftime('%d%m%Y_%H%M%S')
    )
    package_path_base = get_external_data_packages_path(
        user.username
    )

    if not os.path.exists(package_path_base):
        create_external_media(user.username)

    package_path = os.path.join(
        package_path_base, package_name
    )
    
    if metadata:
        # prepare metadata table here
        pass

    if USE_7ZIP:
        # alternative (faster) system-based method to build an archive
        # e.g. 7z a -m0=Copy {package_name}.7z {file_paths}
        pass

    else:
        with zipfile.ZipFile(package_path, 'w', allowZip64=True) as zipf:
            for resource in resources:
                filename = '.'.join(
                    [resource.prefixed_name, resource.mime_type.split('/')[1]]
                )
                zipf.write(
                    "%s/%s" % (
                        settings.MEDIA_ROOT, str(resource.file)
                    ),
                    filename
                )
        zipf.close()

    user_data_package_obj = UserDataPackage(
        user=user, date_created=timestamp,
        package_type=PackageType.MEDIA_FILES
    )
    user_data_package_obj.package.name = os.path.join(
        user.username,
        ExternalStorageSettings.DATA_PACKAGES,
        package_name
    )
    user_data_package_obj.save()
    
    msg = (
        'The requested data package: <strong>{name}</strong> has been successfully generated.'
    )
    
    return msg.format(
        name=package_name
    )




