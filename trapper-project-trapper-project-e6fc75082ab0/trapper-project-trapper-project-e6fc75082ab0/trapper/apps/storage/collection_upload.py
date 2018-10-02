# -*- coding: utf-8 -*-
"""
This module contains a logic responsible for handling the process of
uploading collections of resources.
"""

import os
import zipfile
import yaml
import pytz

from yaml.reader import ReaderError
from yaml.scanner import ScannerError

from StringIO import StringIO
from pykwalify.core import Core, SchemaError, CoreError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.apps import apps
from django.utils import dateparse
from django.utils.timezone import now

from trapper.apps.accounts.utils import get_pretty_username
from trapper.apps.geomap.models import Deployment
from trapper.apps.research.models import (
    ResearchProject, ResearchProjectCollection
)
from trapper.apps.storage.taxonomy import ResourceMimeType


class CollectionProcessorException(Exception):
    """Default exception"""
    pass


class CollectionProcessor(object):
    """
    Class containing a logic necessary to process collection's definition 
    (YAML) and data (ZIP archive) files.
    """
    SEPARATOR = '\n'

    def __init__(self, definition_file, archive_file=None, owner=None):
        """
        Initialize collection processor
        :param definition_file: yaml configuration for `archive_file`
        :param archive_file: when file is uploaded using a web form then
            `archive_file` is `UploadedFile` instance; if it is preselected
            from a list of external media then it is a *full path* to a file
        :param owner: instance of a user
        """
        self.resource_model = apps.get_model('storage', 'Resource')
        self.definition_file = definition_file
        self.definition_data = self.process_definition()
        self.definition = None

        if isinstance(archive_file, basestring):
            archive_file = open(archive_file, 'rb')

        self.archive_file = archive_file
        self.archive = None
        self.owner = owner
        self.owner_display = get_pretty_username(user=owner)
        self.separator = None
        self.deployments = {}
        self.collections_processed = {}
        self.errors = {}

    def process_definition(self):
        """Parse a definition file into a python dictionary"""
        try:
            data = yaml.load(self.definition_file)
        except (ReaderError, ScannerError):
            data = None
        return data

    def format_validation_errors(self, validator, separator=None):
        """Method used to format validation errors

        :param validator: instance of :class:`pykwalify.Core` validator
            that contains validation errors to be displayed
        :param separator: by default it is a new line, but can be set to e.g. 
        <br/> tag when a message is displayed in a form

        :return: a string with errors message
        """
        if separator is None:
            separator = self.SEPARATOR
        return separator.join(validator.validation_errors)

    @property
    def schema(self):
        """Collection processor uses yaml schema to check if a definition file 
        is correct. The YAML schema is implemented with:
        `pykwalify <https://github.com/Grokzen/pykwalify>`_
        """
        return os.path.join(
            settings.PROJECT_ROOT, 'apps/storage/schema/collection_schema.yaml'
        )

    def validate_definition(self, separator=None):
        """
        Check for possible errors within a definition file.
        """
        if separator is None:
            separator = self.SEPARATOR
        self.separator = separator

        try:
            validator = Core(
                source_data=self.definition_data, schema_files=[self.schema]
            )
        except (CoreError, UnicodeEncodeError), e:
            return 'This is not a valid YAML definition file.'

        try:
            self.definition = validator.validate(raise_exception=True)
        except SchemaError:
            return (
                'Error when opening the definition file. YAML syntax might '
                'be invalid.{separator}Details:{separator}{err}'.format(
                    separator=separator,
                    err=self.format_validation_errors(
                        validator=validator, separator=separator
                    )
                )
            )

        errors = []
        for collection_def in self.definition['collections']:
            for field, value in collection_def.items():
                handler = getattr(
                    self, 'clean_{field}'.format(field=field), None
                )
                if callable(handler):
                    errors.append(
                        handler(
                            value=value, collection_name=collection_def['name']
                        )
                    )

        errors = filter(None, errors)
        if errors:
            return self.separator.join(errors)

    def clean_deployments(self, value, collection_name):
        """Check if given deployment exists in a database and if user that
        try to upload a collection has enough permissions to use it."""
        status = None
        self.deployments[collection_name] = []
        for deployment_def in value:
            deployment_id = deployment_def['deployment_id']
            try:
                deployment = Deployment.objects.get(deployment_id=deployment_id)
            except Deployment.DoesNotExist:
                status = 'Deployment {deployment} does not exist'.format(
                    deployment=deployment_id
                )
            else:
                if not deployment.can_update(self.owner):
                    status = (
                        'User {user} has not enough permissions to use the'
                        'deployment {deployment}'.format(
                            user=self.owner_display, deployment=deployment_id
                        )
                    )
                else:
                    self.deployments[collection_name].append(deployment)
        return status

    def clean_project_name(self, value, collection_name):
        """Check if given research project exists in a database and if user that
        try to upload a collection has enough permissions to use it."""
        status = None
        try:
            project = ResearchProject.objects.get(acronym=value)
        except ResearchProject.DoesNotExist:
            status = 'Research project {project} does not exist'.format(
                project=value
            )
        else:
            if not project.can_view(self.owner):
                status = (
                    'User {user} has not enough permissions to use the '
                    'project {project}'.format(
                        user=self.owner_display, project=value
                    )
                )
        return status

    def clean_managers(self, value):
        """Check if managers exist in a database."""
        User = get_user_model()
        status = []
        for user_def in value:
            username = user_def['username']
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                status.append((
                    'User {user} does not exist'.format(user=username)
                ))
        if status:
            return self.separator.join(status)

    def read_from_zip(self, item):
        """Read an item from a zip archive. Item is a name of a file in
        an archive or a ZipInfo object."""
        try:
            bin_data = self.archive.read(item)
            temp_handle = StringIO()
            temp_handle.write(bin_data)
            temp_handle.seek(0)
        except zipfile.BadZipfile:
            raise CollectionProcessorException(
                'File {n} from the archive could not be processed'.format(
                    n=item.filename
                )
            )
        except zipfile.LargeZipFile:
            raise CollectionProcessorException(
                'Your file is too big and the ZIP64 functionality is '
                'not available.'
            )
        return temp_handle

    def build_resource(
            self, resource_def, resources_dir,
            timestamp, deployment=None
    ):
        """
        """
        MEDIA_EXT = ResourceMimeType.MEDIA_EXTENSIONS
        resource_model = self.resource_model

        file_ext = os.path.splitext(resource_def['file'])[-1]
        extra_file = resource_def.get('extra_file','')

        if not file_ext.lower() in MEDIA_EXT:
            error = 'Not allowed mime type: *.{file_ext}'.format(
                file_ext
            )
            return (None, error)

        if extra_file:
            extra_file_ext = os.path.splitext(extra_file)[-1]
            if not extra_file_ext.lower() in MEDIA_EXT:
                error = 'Not allowed mime type: *.{extra_file_ext}'.format(
                    extra_file_ext
                )
                return (None, error)

        if deployment:
            base_path = os.path.join(
                resources_dir, deployment.deployment_id
            )
        else:
            base_path = resources_dir

        file_path = os.path.join(
            base_path, resource_def['file']
        )
        bin_data_file = self.read_from_zip(
            file_path
        )

        date_recorded = dateparse.parse_datetime(
            resource_def['date_recorded']
            )
        if not date_recorded:
            error = 'Could not parse date recorded timestamp: {date}'.format(
                date=resource_def['date_recorded']
            )
            return (None, error)
        date_recorded = date_recorded.replace(tzinfo=pytz.UTC)

        resource = resource_model(
            name=resource_def['name'],
            owner=self.owner,
            date_recorded=date_recorded,
            date_uploaded=timestamp
        )

        if deployment:
            resource.deployment = deployment

        suf_file = SimpleUploadedFile(
            os.path.split(resource.file.name)[-1],
            bin_data_file.read(), content_type=file_ext
        )
        resource.file.save(
            resource_def['file'], suf_file, save=False
        )

        if extra_file:
            extra_file_path = os.path.join(
                base_path, extra_file
            )
            bin_data_extra_file = self.read_from_zip(
                extra_file_path
            )

            suf_extra_file = SimpleUploadedFile(
                os.path.split(resource.file.name)[-1],
                bin_data_extra_file.read(),
                content_type=extra_file_ext
            )
            resource.extra_file.save(
                resource_def['file'], suf_extra_file,
                save=False
            )
        resource.update_metadata()

        return (resource, None)


    @transaction.atomic
    def create(self):
        """When definition and data files are correct,
        :class:`apps.storage.models.Collection` instances and
        :class:`apps.storage.models.Resource` instances are created.

        In case of any errors the process is stopped and a proper message 
        is displayed to a user.

        """
        from trapper.apps.storage.tasks import celery_update_thumbnails
        User = get_user_model()

        collection_model = apps.get_model('storage', 'Collection')

        errors = self.validate_definition()
        if errors:
            raise CollectionProcessorException(
                'Your config file is invalid: {errors}'.format(
                    errors=errors
                )
            )

        collections = {}

        for collection_def in self.definition['collections']:
            name = collection_def['name']
            resources_dir = collection_def['resources_dir']
            free_resources = collection_def.get('resources', [])
            resources = {}
            project_name = collection_def.get('project_name', None)

            research_project = None
            if project_name:
                research_project = ResearchProject.objects.get(
                    acronym=project_name
                )

            managers = []
            manager_usernames = [
                item['username'] for item in collection_def.get('managers', [])
            ]
            if manager_usernames:
                managers = User.objects.filter(username__in=manager_usernames)

            collection, _created = collection_model.objects.get_or_create(
                name=name,
                owner=self.owner,
            )

            for item in managers:
                collection.managers.add(item)

            if research_project:
                ResearchProjectCollection.objects.get_or_create(
                    project=research_project,
                    collection=collection
                )

            collections[resources_dir] = {
                'collection': collection,
                'resources': resources
            }
            self.collections_processed[collection.name] = {}
            self.errors[collection.name] = {}

            try:
                self.archive = zipfile.ZipFile(self.archive_file)
            except ValueError:
                # I/O operation on closed file
                # This can occur for celery tasks
                self.archive_file.file.open()
                self.archive = zipfile.ZipFile(self.archive_file.file)

            if not zipfile.is_zipfile(self.archive_file):
                raise CollectionProcessorException(
                    "This is not a valid zip file: {file}.".format(
                        file=self.archive_file.file.name
                    )
                )

            resources_list = []
            timestamp = now()
            deployments_objects = self.deployments[name]
            deployments_objects.sort(key=lambda x: x.deployment_id)
            deployments_definitions = collection_def.get('deployments', [])
            deployments_definitions.sort(key=lambda x: x['deployment_id'])
            deployments = zip(deployments_objects, deployments_definitions)

            for _deployment in deployments:
                deployment = _deployment[0]
                self.collections_processed[collection.name][
                    deployment.deployment_id
                ] = []
                self.errors[collection.name][
                    deployment.deployment_id
                ] = []
                for resource_def in _deployment[1]['resources']:

                    try: 
                        resource, error = self.build_resource(
                            resource_def, resources_dir,
                            timestamp, deployment
                        )
                    except Exception, e:
                        resource = None
                        error = str(e)

                    if not error:
                        resources_list.append(resource)
                        self.collections_processed[collection.name][
                            deployment.deployment_id
                        ].append(resource.name)
                    else:
                        self.errors[collection.name][
                            deployment.deployment_id
                        ].append((resource_def['file'], error))

                if not self.errors[collection.name][
                    deployment.deployment_id
                ]:
                    self.errors[collection.name].pop(
                        deployment.deployment_id
                    )

            self.collections_processed[collection.name][
                'free_resources'
            ] = []
            self.errors[collection.name][
                'free_resources'
            ] = []
            for resource_def in free_resources:
                
                try:
                    resource, error = self.build_resource(
                        resource_def, resources_dir,
                        timestamp
                    )
                except Exception, e:
                    resource = None
                    error = str(e)

                if not error:
                    resources_list.append(resource)
                    self.collections_processed[collection.name][
                        'free_resources'
                    ].append(resource.name)
                else:
                    self.errors[collection.name][
                        'free_resources'
                    ].append((resource_def['file'], error))
            if not self.errors[collection.name][
                'free_resources'
            ]:
                self.errors[collection.name].pop('free_resources')
            self.resource_model.objects.bulk_create(resources_list)
            resources = self.resource_model.objects.filter(
                date_uploaded=timestamp
            )
            resources_pks = [k.pk for k in resources]
            collection.resources.add(*resources_pks)
            celery_update_thumbnails.delay(resources)
            if not self.errors[collection.name]:
                self.errors.pop(collection.name)
