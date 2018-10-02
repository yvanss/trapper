# -*- coding: utf-8 -*-
"""Extensions that helps testing code"""

import json
import os
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.test.testcases import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.lorem_ipsum import words
from django.test.utils import override_settings
from django.contrib.gis.geos.point import Point
from django.utils.timezone import now
from django.db import connection
from psycopg2.extras import register_hstore

from trapper.apps.common.utils.identity import create_hashcode
from trapper.apps.storage.models import (
    Resource, Collection, CollectionMember
)
from trapper.apps.storage.taxonomy import ResourceStatus, CollectionStatus
from trapper.apps.research.models import (
    ResearchProject, ResearchProjectRole, ResearchProjectCollection
)
from trapper.apps.research.taxonomy import ResearchProjectStatus
from trapper.apps.geomap.models import Location, Deployment
from trapper.apps.accounts.utils import create_external_media
from trapper.apps.media_classification.models import (
    ClassificationProject, ClassificationProjectRole,
    ClassificationProjectCollection, Classificator, Sequence, Classification,
    UserClassification
)

User = get_user_model()

__all__ = ['ExtendedTestCase', 'TestActorsMixin', 'ResourceTestMixin']


def create_user(username, is_active=True, is_superuser=False):
    """Method used by metaclass for dynamic createion `create_<username>`
    methods
    """
    def _inner(self):
        email = '{u}@example.com'.format(u=username)

        is_admin = bool(is_superuser)
        params = {
            'username': username,
            'email': email,
            'is_active': bool(is_active),
            'is_staff': is_admin,
            'is_superuser': is_admin
        }

        user = User(**params)
        user.set_password(username)
        user.save()

        setattr(self, '{u}_email'.format(u=username), email)
        setattr(self, '{u}_passwd'.format(u=username), username)
        setattr(self, username, user)
    return _inner


def login_user(username):
    """Method used by metaclass for dynamic createion `login_<username>`
    methods
    """
    def _inner(self):
        logged_in = self.client.login(username=username, password=username)
        self.assertTrue(logged_in)
        create_external_media(username)
        return logged_in
    return _inner


class ActorsMixinMetaclass(type):

    def __new__(mcs, name, bases, attrs):
        new_class = super(ActorsMixinMetaclass, mcs).__new__(
            mcs, name, bases, attrs
        )

        active_users = attrs.pop('active_users', [])
        inactive_users = attrs.pop('inactive_users', [])
        sysadmins = attrs.pop('sysadmins', [])

        for username in active_users:
            summon_name = 'summon_{u}'.format(u=username)
            login_name = 'login_{u}'.format(u=username)

            setattr(new_class, summon_name, create_user(username))
            setattr(new_class, login_name, login_user(username))

        for username in sysadmins:
            summon_name = 'summon_{u}'.format(u=username)
            login_name = 'login_{u}'.format(u=username)

            setattr(
                new_class,
                summon_name,
                create_user(username, is_superuser=True)
            )
            setattr(new_class, login_name, login_user(username))

        for username in inactive_users:
            summon_name = 'summon_{u}'.format(u=username)

            setattr(
                new_class, summon_name, create_user(username, is_active=False)
            )

        return new_class


class TestActorsMixin(object):
    """Mixin with actors used for testing.

    * active_users - each user will be able to login to project
    * sysadmins - like `active_users` but users will be superusers
    * inactive_users - those users will have created disabled accounts

    For each user special method is create: `summon_<username>`. I.e. for
    `alice` method will be called `summon_alice`

    For each active user (active_users and sysadmins) will additionaly have
    own method `login_<username>`. I.e. for `alice` method will be called
    `login_alice`. Inactive users won't get such methods since they cannot
    login anyway.

    If more actors are needed just add them to proper list.
    """

    __metaclass__ = ActorsMixinMetaclass

    active_users = ['alice', 'ziutek', 'john']
    sysadmins = ['root']
    inactive_users = ['eric']


class LocationTestMixin(object):

    def create_location(self, owner, **kwargs):

        params = {
            'name': words(3, common=False),
            'is_public': True,
            'owner': owner,
            'coordinates': Point(x=50, y=50),
        }

        params.update(kwargs or {})

        location = Location.objects.create(**params)
        return location


class DeploymentTestMixin(object):

    def create_deployment(self, owner, **kwargs):

        params = {
            'deployment_code': words(1, common=False),
            'location': self.create_location(owner=owner),
            'start_date': now(),
            'end_date': now(),
            'owner': owner
        }

        params.update(kwargs or {})

        deployment = Deployment.objects.create(**params)
        return deployment


class ResourceTestMixin(LocationTestMixin, DeploymentTestMixin):
    def create_resource(
        self, owner, status=None, file_content=None, managers=None,
        **resource_kwargs
    ):

        status = status or ResourceStatus.ON_DEMAND
        if not file_content:
            file_path = os.path.join(self.SAMPLE_MEDIA_PATH, 'image_1.jpg')
            with open(file_path) as handler:
                file_content = handler.read()

        file_name = u"{name}.png".format(name=create_hashcode())

        params = {
            'name': words(3, common=False),
            'file': SimpleUploadedFile(file_name, file_content),
            'date_recorded': now(),
            'status': status,
            'owner': owner
        }
        params.update(**resource_kwargs)

        resource = Resource.objects.create(**params)

        if managers:
            resource.managers = managers

        return resource


class CollectionTestMixin(ResourceTestMixin):

    def create_collection(
        self, owner, status=None, resources=None, managers=None, roles=None
    ):

        status = status or CollectionStatus.ON_DEMAND
        resources = resources or [self.create_resource(owner=owner)]

        collection = Collection.objects.create(
            name=words(3, common=False),
            status=status,
            owner=owner
        )
        collection.resources = resources

        if managers:
            collection.managers = managers

        if roles:
            for user, level in roles:
                CollectionMember.objects.create(
                    user=user,
                    collection=collection,
                    level=level
                )
        return collection


class ResearchProjectTestMixin(object):

    def create_research_project(
        self, owner, status=None, collections=None, roles=None, name=None
    ):

        if status is None:
            status = ResearchProjectStatus.APPROVED
        name = name or words(3, common=False)
        acronym = name[:3]

        project = ResearchProject.objects.create(
            name=name,
            acronym=acronym,
            status=status,
            owner=owner
        )

        if collections:
            project.collections = collections

        if roles:
            for user, role_level in roles:
                ResearchProjectRole.objects.create(
                    project=project,
                    user=user,
                    name=role_level
                )
        return project

    def create_research_project_collection(self, project, collection):
        return ResearchProjectCollection.objects.create(
            project=project,
            collection=collection
        )


class ClassificationProjectTestMixin(object):

    def create_classification_project(
        self, owner, research_project, collections=None, roles=None, **kwargs
    ):
        if 'name' not in kwargs:
            name = words(3, common=False)
        else:
            name = kwargs['nmae']

        params = {
            'name': name,
            'research_project': research_project,
            'owner': owner
        }
        params.update(kwargs or {})

        project = ClassificationProject.objects.create(**params)

        if collections:
            project.collections = collections

        if roles:
            for user, role_level in roles:
                ClassificationProjectRole.objects.create(
                    classification_project=project,
                    user=user,
                    name=role_level
                )
        return project

    def create_classification_project_collection(self, project, collection):
        return ClassificationProjectCollection.objects.create(
            project=project,
            collection=collection
        )


class ClassificatorTestMixin(object):

    def create_classificator(self, owner, **kwargs):
        if 'name' not in kwargs:
            name = words(3, common=False)
        else:
            name = kwargs['name']

        params = {
            'name': name,
            'owner': owner
        }
        params.update(kwargs or {})
        classificator = Classificator.objects.create(**params)

        return classificator


class SequenceTestMixin(object):

    def create_sequence(self, owner, collection, resources=None, **kwargs):

        if 'sequence_id' not in kwargs:
            sequence_id = words(3, common=False)
        else:
            sequence_id = kwargs['sequence_id']

        params = {
            'sequence_id': sequence_id,
            'created_by': owner,
            'collection': collection
        }
        params.update(kwargs or {})

        sequence = Sequence.objects.create(**params)

        if resources is not None:
            sequence.resources = resources

        return sequence


class ClassificationTestMixin(object):

    def create_user_classification(self, owner, classification):
        user_classification, created = UserClassification.objects.get_or_create(
            classification=classification,
            owner=owner,
            defaults={
                'created_at': now(),
                'static_attrs': {'Item1': 'Val1', 'Item2': 'Val2'}
            }
        )
        return user_classification

    def create_classification(
        self, resource, collection, project, owner, status=None
    ):

        classification, created = Classification.objects.get_or_create(
            resource=resource,
            project=project,
            collection=collection,
            owner=owner,
            defaults={
                'created_at': now(),
                'static_attrs': {}
            }
        )
        if status:
            user_classification = self.create_user_classification(
                owner, classification
            )
            classification.status = status
            classification.approved_at = now()
            classification.approved_by = owner
            classification.approved_source = user_classification
            classification.static_attrs = user_classification.static_attrs
            classification.save()
        else:
            user_classification = None
        return classification, user_classification 



@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(suffix='-trapper'),
    EXTERNAL_MEDIA_ROOT=tempfile.mkdtemp(suffix='-trapper-external'),
    CELERY_DATA_ROOT=tempfile.mkdtemp(suffix='-celery-data'),
    CELERY_ENABLED=False,
)
class ExtendedTestCase(TestCase, TestActorsMixin):
    """Extended version of :class:`TestCase` that
    add by default:

    * clean cache
    * logout client on :func:`tearDown`

    This class also add new assertions
    """

    TEST_DATA_PATH = os.path.join(settings.PROJECT_ROOT, '..', 'test_data')
    SAMPLE_MEDIA_PATH = os.path.join(TEST_DATA_PATH, 'media_samples')

    TEST_PK = 1000

    def setUp(self):
        """Before each test is runned run some default actions:
        * clear cache
        * assign mailbox
        """
        super(ExtendedTestCase, self).setUp()
        cache.clear()

        self.mail = mail
        self.mail.outbox = []

        # https://github.com/djangonauts/django-hstore/issues/93
        register_hstore(connection.connection)

    def tearDown(self):
        """Make sure that client is logged out after test"""
        self.client.logout()

    def _process_request(self, url, method, data, follow=False):
        data = data or {}
        if method == 'post':
            response = self.client.post(url, data=data, follow=follow)
        else:
            response = self.client.get(url, follow=follow)
        return response

    def _process_messages(self, response):
        """Prepare list of messages from django messaging framework"""
        try:
            storage = response.context['messages']
        except TypeError:
            messages = []
        else:
            messages = storage._loaded_data

        message_body_list = []
        for message in messages:
            message_body_list.append(message.message)
        return message_body_list

    def assert_auth_required(self, url, method='get', data=None, follow=False):
        """Checks that user is required to login before access given url"""

        response = self._process_request(url, method, data, follow)

        self.assertEqual(response.status_code, 302, response.status_code)
        self.assertTrue(response.has_header('location'))
        location = response._headers['location'][1]

        response_url = '{login_url}?next={dest_url}'.format(
            login_url=settings.LOGIN_URL,
            dest_url=url
        )
        self.assertTrue(response_url in location, response_url)
        return response

    def assert_auth_required_json(
        self, url, method='get', data=None, follow=False
    ):
        """Checks that user is required to login before access given url.
        This is json response assert"""

        response = self._process_request(url, method, data, follow)

        self.assertEqual(response.status_code, 200, response.status_code)
        content = json.loads(response.content)
        self.assertFalse(content['status'])
        self.assertEqual(
            content['msg'], "Authentication required", content['msg']
        )
        return response

    def assert_forbidden(self, url, method='get', data=None, follow=False):
        """Assert that user should not have access to given url"""
        response = self._process_request(url, method, data, follow)
        self.assertEqual(response.status_code, 403, response.status_code)
        return response

    def assert_access_granted(
        self, url, method='get', data=None, follow=False
    ):
        """Assert that user should have access to given url"""
        response = self._process_request(url, method, data, follow)
        self.assertEqual(response.status_code, 200, response.status_code)
        return response

    def assert_not_allowed(self, url, method='get', data=None, follow=False):
        """Assert that method is not allowed for given url"""
        response = self._process_request(url, method, data, follow)
        self.assertEqual(response.status_code, 405, response.status_code)
        return response

    def assert_redirect(
        self, url, redirection=None, method='get', data=None, follow=False
    ):
        """Assert that user should have access to given url"""
        response = self._process_request(url, method, data, follow=follow)
        self.assertEqual(response.status_code, 302, response.status_code)
        if redirection:
            self.assertTrue(response.has_header('location'))
            location = response._headers['location'][1]
            self.assertTrue(redirection in location, location)
        return response

    def assert_context_variable(self, response, variable):
        """Assert that response context holds given variable"""
        context = response.context[-1]
        self.assertIn(variable, context)
        return context[variable]

    def assert_json_context_variable(self, response, variable):
        """Assert that response content is json and holds given variable"""
        context = json.loads(response.content)
        self.assertIn(variable, context)
        return context[variable]

    def assert_invalid_pk(self, response, field='changed'):
        """Assert that invalid pk is not returned in list of changed
        items when post data is submitted using `pks`"""
        field_data = self.assert_json_context_variable(response, field)
        self.assertNotIn(self.TEST_PK, field_data)

    def assert_has_message(self, response, msg):
        """Check if given message was added using django messages framework"""
        message_list = self._process_messages(response)
        self.assertIn(
            msg, message_list,
            u"Message: '{msg}' should be displayed but is not.".format(
                msg=msg
            )
        )

    def assert_has_no_message(self, response, msg):
        """
        Check if given message was not added using django messages framework
        """
        message_list = self._process_messages(response)
        self.assertNotIn(
            msg, message_list,
            u"Message: '{msg}' should not be displayed but is.".format(
                msg=msg
            )
        )
