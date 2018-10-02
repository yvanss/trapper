# -*- coding: utf-8 -*-

import datetime
import json
import os
import shutil

from django.core.urlresolvers import reverse
from django.utils.lorem_ipsum import words
from django.utils.timezone import now, localtime

from trapper.apps.accounts.utils import get_external_resources_path
from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, ResourceTestMixin, CollectionTestMixin,
)
from trapper.apps.storage.taxonomy import (
    ResourceStatus, CollectionStatus
)
from trapper.apps.storage.models import Resource


class BaseResourceTestCase(ExtendedTestCase, ResourceTestMixin):
    def setUp(self):
        super(BaseResourceTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

        self.resource_public = self.create_resource(
            owner=self.alice, status=ResourceStatus.PUBLIC
        )
        self.resource_ondemand = self.create_resource(
            owner=self.alice, status=ResourceStatus.ON_DEMAND
        )
        self.resource_private = self.create_resource(
            owner=self.alice, status=ResourceStatus.PRIVATE
        )

    def get_resource_create_url(self):
        """Default url for creating resource"""
        return reverse('storage:resource_create')

    def get_resource_details_url(self, resource):
        """Default url for details"""
        return reverse('storage:resource_detail', kwargs={'pk': resource.pk})

    def get_resource_update_url(self, resource):
        """Default url for update"""
        return reverse('storage:resource_update', kwargs={'pk': resource.pk})

    def get_resource_delete_url(self, resource):
        """Default url for delete"""
        return reverse('storage:resource_delete', kwargs={'pk': resource.pk})

    def get_collection_create_url(self):
        """Default url for creating collection"""
        return reverse('storage:collection_create')

    def get_collection_append_url(self):
        """Default url for appending collection"""
        return reverse('storage:collection_append')


class AnonymousResourceTestCase(BaseResourceTestCase):
    """Resource logic for anonymous users"""

    def test_resource_list(self):
        """Anonymous user can access to resources list"""
        url = reverse('storage:resource_list')
        self.assert_access_granted(url)

    def test_resource_json(self):
        """Anonymous user can see only PUBLIC resources"""

        url = reverse('storage:api-resource-list')
        response = self.client.get(url)
        content = json.loads(response.content)['results']

        resource_pk_list = [item['pk'] for item in content]

        self.assertIn(
            self.resource_public.pk, resource_pk_list, 'Public not shown'
        )
        self.assertNotIn(
            self.resource_ondemand.pk, resource_pk_list, 'OnDemand shown'
        )
        self.assertNotIn(
            self.resource_private.pk, resource_pk_list, 'Private shown'
        )

    def test_resource_details(self):
        """Anonymous user has no permissions to access non-public details."""
        url_private = self.get_resource_details_url(
            resource=self.resource_private
        )
        url_ondemand = self.get_resource_details_url(
            resource=self.resource_ondemand
        )
        url_public = self.get_resource_details_url(
            resource=self.resource_public
        )

        self.assert_forbidden(url=url_private)
        self.assert_forbidden(url=url_ondemand)
        self.assert_access_granted(url=url_public)

    def test_resource_create(self):
        """Anonymous user has to login before creating resource"""
        url = self.get_resource_create_url()
        self.assert_auth_required(url=url)

    def test_resource_delete(self):
        """Anonymous user has to login before delete."""
        url = reverse('storage:resource_delete', kwargs={'pk': 1})
        self.assert_auth_required_json(url=url, method='get')
        self.assert_auth_required_json(url=url, method='post')

    def test_resource_delete_multiple(self):
        """Anonymous user has to login before delete.
        Delete is handled by Ajax"""
        url = reverse('storage:resource_delete_multiple')
        self.assert_auth_required_json(url=url, method='post')

    def test_resource_update(self):
        """Anonymous user has no permissions to update."""
        url = reverse('storage:resource_update', kwargs={'pk': 1})
        self.assert_forbidden(url=url, method='post')

    def test_bulk_update(self):
        """Anonymous user has to login before using bulk update."""
        url = reverse('storage:resource_bulk_update')
        self.assert_auth_required(url=url, method='get')
        self.assert_auth_required(url=url, method='post')

    def test_define_prefix(self):
        """Anonymous user has to login before use define prefix."""
        url = reverse('storage:resource_define_prefix')
        self.assert_auth_required_json(url=url, method='post')


class ResourcePermissionsDetailsTestCase(BaseResourceTestCase):
    """Details permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ResourcePermissionsDetailsTestCase, self).setUp()
        self.login_alice()

    def test_details_owner(self):
        """Resource owner can access details"""
        resource = self.create_resource(owner=self.alice)
        url = self.get_resource_details_url(resource=resource)
        self.assert_access_granted(url)

    def test_details_manager(self):
        """Resource manager can access details"""
        resource = self.create_resource(
            owner=self.ziutek, managers=[self.alice]
        )

        url = self.get_resource_details_url(resource=resource)
        self.assert_access_granted(url)

    def test_details_role_access(self):
        """TODO: access from collection"""

    def test_details_no_roles(self):
        """Other users can not access a resource"""
        resource = self.create_resource(owner=self.ziutek,)
        url = self.get_resource_details_url(resource=resource)
        self.assert_forbidden(url)


class ResourcePermissionsUpdateTestCase(BaseResourceTestCase):
    """Update resource permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ResourcePermissionsUpdateTestCase, self).setUp()
        self.login_alice()

    def test_update_owner(self):
        """Resource owner can update resource"""
        resource = self.create_resource(owner=self.alice)
        url = self.get_resource_update_url(resource=resource)
        self.assert_access_granted(url, method='post', data={'name': 'test'})

    def test_update_manager(self):
        """Resource manager can update resource"""
        resource = self.create_resource(
            owner=self.ziutek, managers=[self.alice]
        )
        url = self.get_resource_update_url(resource=resource)
        self.assert_access_granted(url, method='post', data={'name': 'test'})

    def test_update_no_roles(self):
        """Other users can not update a resource"""
        resource = self.create_resource(owner=self.ziutek)
        url = self.get_resource_update_url(resource=resource)
        self.assert_forbidden(url, method='post', data={'name': 'test'})


class ResourcePermissionsDeleteTestCase(BaseResourceTestCase):
    """
    Delete resource permission logic for logged in user

    .. note::
        Delete multiple uses the same permission logic
    """
    def setUp(self):
        """Login alice by default for all tests, and prepare redirect url
        which is default for all tests"""
        super(ResourcePermissionsDeleteTestCase, self).setUp()
        self.login_alice()
        self.redirection = reverse('storage:resource_list')

    def test_delete_owner(self):
        """Resource owner can delete resource"""
        resource = self.create_resource(owner=self.alice)
        url = self.get_resource_delete_url(resource=resource)
        self.assert_redirect(url, self.redirection)

    def test_delete_manager(self):
        """Resource manager can delete resource"""
        resource = self.create_resource(
            owner=self.ziutek, managers=[self.alice]
        )
        url = self.get_resource_delete_url(resource=resource)
        self.assert_redirect(url, self.redirection)

    def test_delete_no_roles(self):
        """Other users can not delete a resource"""
        resource = self.create_resource(owner=self.ziutek)
        url = self.get_resource_delete_url(resource=resource)
        self.assert_forbidden(url)


class ResourcePermissionsBulkUpdateTestCase(BaseResourceTestCase):
    """Bulk update permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests, and prepare redirect url
        which is default for all tests"""
        super(ResourcePermissionsBulkUpdateTestCase, self).setUp()
        self.login_alice()
        self.redirection = reverse('storage:resource_list')

    def _call_helper(self, resource):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        url = reverse('storage:resource_bulk_update')

        data = {
            'pks': [resource.pk],
            'status': ResourceStatus.PUBLIC
        }
        response = self.assert_access_granted(url, method='post', data=data)
        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_bulk_update_owner(self):
        """Owner can perform bulk operation on resources"""
        resource = self.create_resource(owner=self.alice)
        status = self._call_helper(resource=resource)
        self.assertTrue(status)

    def test_bulk_update_manager(self):
        """Manager can perform bulk operation on resources"""
        resource = self.create_resource(
            owner=self.ziutek, managers=[self.alice]
        )
        status = self._call_helper(resource=resource)
        self.assertTrue(status)

    def test_bulk_update_no_roles(self):
        """Other users can not bulk update a resource"""
        resource = self.create_resource(owner=self.ziutek)
        status = self._call_helper(resource=resource)
        self.assertFalse(status)


class ResourcePermissionsDefinePrefixTestCase(BaseResourceTestCase):
    """Define prefix permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests, and prepare redirect url
        which is default for all tests and create default deployment"""
        super(ResourcePermissionsDefinePrefixTestCase, self).setUp()
        self.login_alice()
        self.redirection = reverse('storage:resource_list')
        self.deployment = self.create_deployment(owner=self.alice)

    def _call_helper(self, resource):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        url = reverse('storage:resource_define_prefix')

        data = {
            'pks': [resource.pk],
            'custom_prefix': 'test-prefix-'
        }
        response = self.assert_access_granted(url, method='post', data=data)
        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_define_prefix_owner(self):
        """Owner can change prefix on resources"""
        resource = self.create_resource(
            owner=self.alice, deployment=self.deployment
        )
        status = self._call_helper(resource=resource)
        self.assertTrue(status)

    def test_define_prefix_manager(self):
        """Manager can change prefix on resources"""
        resource = self.create_resource(
            owner=self.ziutek, managers=[self.alice], deployment=self.deployment
        )
        status = self._call_helper(resource=resource)
        self.assertTrue(status)

    def test_define_prefix_no_roles(self):
        """Other users can not bulk update a resource"""
        resource = self.create_resource(
            owner=self.ziutek, deployment=self.deployment,
        )
        status = self._call_helper(resource=resource)
        self.assertFalse(status)


class ResourcePermissionsCreateCollectionTestCase(BaseResourceTestCase):
    """Create collection permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ResourcePermissionsCreateCollectionTestCase, self).setUp()
        self.login_alice()

    def test_create_collection_owner(self):
        """Owner can use a resource to create a collection"""
        resource = self.create_resource(owner=self.alice)
        url = self.get_collection_create_url()

        data = {
            'name': 'test-collection',
            'status': CollectionStatus.PUBLIC,
            'resources_pks': resource.pk
        }
        response = self.assert_access_granted(url, method='post', data=data)
        self.assertTrue(
            self.assert_json_context_variable(response, 'success')
        )

    def test_create_collection_manager(self):
        """Manager can use a resource to create a collection"""
        resource = self.create_resource(
            owner=self.ziutek, managers=[self.alice]
        )
        url = self.get_collection_create_url()

        data = {
            'name': 'test-collection',
            'status': CollectionStatus.PUBLIC,
            'resources_pks': resource.pk
        }
        response = self.assert_access_granted(url, method='post', data=data)
        self.assertTrue(
            self.assert_json_context_variable(response, 'success')
        )

    def test_create_collection_role_access(self):
        """TODO: access from collection"""

    def test_create_collection_no_roles(self):
        """Other users can not use a resource to create a collection"""
        resource = self.create_resource(owner=self.ziutek)
        url = self.get_collection_create_url()

        data = {
            'name': 'test-collection',
            'status': CollectionStatus.PUBLIC,
            'resources_pks': resource.pk
        }
        response = self.assert_access_granted(url, method='post', data=data)
        self.assertFalse(
            self.assert_json_context_variable(response, 'success')
        )


class ResourcePermissionsAppendCollectionTestCase(
    BaseResourceTestCase, CollectionTestMixin
):
    """Append to collection permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests, and prepare default
        collection and redirection url"""
        super(ResourcePermissionsAppendCollectionTestCase, self).setUp()
        self.login_alice()
        self.collection = self.create_collection(owner=self.alice)
        self.redirect_url = reverse(
            'storage:collection_detail', kwargs={'pk': self.collection.pk}
        )

    def get_collection_detail_url(self):
        return

    def test_append_collection_owner(self):
        """Owner can append resource to collection"""
        resource = self.create_resource(owner=self.alice)

        url = self.get_collection_append_url()

        data = {
            'collection': self.collection.pk,
            'resources': resource.pk
        }
        self.assert_redirect(
            url, redirection=self.redirect_url, method='post', data=data
        )

    def test_append_collection_manager(self):
        """Manager can append resource to collection"""
        resource = self.create_resource(
            owner=self.ziutek, managers=[self.alice]
        )
        url = self.get_collection_append_url()

        data = {
            'collection': self.collection.pk,
            'resources': resource.pk
        }
        self.assert_redirect(
            url, redirection=self.redirect_url, method='post', data=data
        )

    def test_create_collection_role_access(self):
        """TODO: access from collection"""

    def test_create_collection_no_roles(self):
        """Other users can not bulk update a resource"""
        resource = self.create_resource(owner=self.ziutek)
        url = self.get_collection_append_url()

        data = {
            'collection': self.collection.pk,
            'resources': resource.pk
        }
        self.assert_forbidden(url, method='post', data=data)


class ResourcePermissionsListTestCase(BaseResourceTestCase):
    """Resource listing permission logic for logged in user"""

    def setUp(self):
        super(ResourcePermissionsListTestCase, self).setUp()
        self.login_alice()

    def test_resource_list(self):
        """Logged in user can access resource lisst"""
        url = reverse('storage:resource_list')
        self.assert_access_granted(url)

    def test_resource_json(self):
        """Logged in user can see

        * PUBLIC resources
        * OnDemand resources even if user has no access to view details
        * Own PRIVATE resources

        User cannot see other's people PRIVATE resources
        """
        url = reverse('storage:api-resource-list')
        self.resource_private_ziutek = self.create_resource(
            owner=self.ziutek, status=ResourceStatus.PRIVATE
        )

        response = self.client.get(url)
        content = json.loads(response.content)['results']
        resource_pk_list = [item['pk'] for item in content]

        self.assertIn(
            self.resource_public.pk, resource_pk_list, 'Public not shown'
        )
        self.assertIn(
            self.resource_ondemand.pk, resource_pk_list, 'OnDemand not shown'
        )
        self.assertIn(
            self.resource_private.pk, resource_pk_list,
            'Private not shown (own)'
        )
        self.assertNotIn(
            self.resource_private_ziutek.pk, resource_pk_list,
            'Private not shown (ziutek)'
        )


class ResourceTestCase(BaseResourceTestCase):
    """Tests related to modifying data for resource by performing various
    accions"""

    def test_resource_create_upload(self):
        """
        Using create view create storage.Resource model instance
        After resource is created user is redirected to details
        page - version where user upload file."""

        deployment = self.create_deployment(owner=self.alice)

        image_file = os.path.join(self.SAMPLE_MEDIA_PATH, 'image_1.jpg')
        url = self.get_resource_create_url()
        self.login_alice()
        name = words(count=5, common=False)
        with open(image_file) as file_handler:
            params = {
                'name': name,
                'date_recorded': '08.08.2015 06:06:06',
                'file': file_handler,
                'status': ResourceStatus.PRIVATE,
                'deployment': deployment.pk
            }
            response = self.client.post(url, params)
            self.assertEqual(response.status_code, 302, response.status_code)
            self.assertTrue(
                Resource.objects.filter(
                    name=name,
                    date_recorded=datetime.datetime(2015, 8, 8, 6, 6, 6),
                    status=ResourceStatus.PRIVATE,
                    deployment=deployment
                ).exists()
            )

    def test_resource_create_preselected(self):
        """
        Using create view create storage.Resource model instance
        After resource is created user is redirected to details
        page - version where user preselect existing file."""
        deployment = self.create_deployment(owner=self.alice)
        image_file = os.path.join(self.SAMPLE_MEDIA_PATH, 'image_1.jpg')
        temp_file = get_external_resources_path(
            self.alice.username, 'image_1.jpg'
        )
        temp_path = os.path.dirname(temp_file)
        # When test is run as single we need to make sure that copying file
        # is made to existing directory
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)
        shutil.copyfile(image_file, temp_file)

        url = self.get_resource_create_url()
        self.login_alice()
        name = words(count=5, common=False)
        params = {
            'name': name,
            'date_recorded': '06.06.2015 06:06:06',
            'preselected_file': 'image_1.jpg',
            'status': ResourceStatus.PRIVATE,
            'deployment': deployment.pk
        }
        response = self.client.post(url, params)

        self.assertEqual(response.status_code, 302, response.status_code)
        self.assertTrue(
            Resource.objects.filter(
                name=name,
                date_recorded=datetime.datetime(2015, 6, 6, 6, 6, 6),
                status=ResourceStatus.PRIVATE,
                deployment=deployment
            ).exists()
        )

    def test_resource_update(self):
        """
        Using update view logged in user that has enough permissions can
        change existing resource.
        """
        self.login_alice()
        deployment = self.create_deployment(owner=self.alice)
        resource = self.create_resource(
            owner=self.alice, status=ResourceStatus.PRIVATE
        )

        url = self.get_resource_update_url(resource=resource)

        date_recorded = now()

        # Time is sent from non-utc timezone
        attributes = {
            'name': 'test_name',
            'status': ResourceStatus.PUBLIC,
            'deployment': deployment.pk,
            'date_recorded': localtime(
                value=date_recorded
            ).strftime('%d.%m.%Y %H:%M:%S')
        }
        self.client.post(url, attributes)

        new_resource = Resource.objects.get(pk=resource.pk)

        self.assertEqual(new_resource.name, attributes['name'])
        self.assertEqual(new_resource.status, attributes['status'])
        self.assertEqual(new_resource.deployment, deployment)

        # We use format to strip miliseconds that aren't sent to backend
        self.assertEqual(
            new_resource.date_recorded.strftime('%d.%m.%Y %H:%M:%S'),
            date_recorded.strftime('%d.%m.%Y %H:%M:%S')
        )

    def test_resource_delete(self):
        """
        Using delete view logged in user that has enough permissions can
        delete existing resource using GET.
        """
        self.login_alice()
        resource = self.create_resource(
            owner=self.alice, status=ResourceStatus.PRIVATE
        )

        url = self.get_resource_delete_url(resource=resource)

        self.client.get(url)
        self.assertFalse(Resource.objects.filter(pk=resource.pk).exists())

    def test_resource_delete_multiple(self):
        """
        Using delete view logged in user that has enough permissions can
        delete multiple resources using POST.
        """
        self.login_alice()
        resource1 = self.create_resource(
            owner=self.alice, status=ResourceStatus.PRIVATE
        )
        resource2 = self.create_resource(
            owner=self.alice, status=ResourceStatus.PRIVATE
        )

        url = reverse('storage:resource_delete_multiple')

        pks_list = [resource1.pk, resource2.pk, self.TEST_PK]

        response = self.client.post(
            url, data={'pks': ",".join(map(str, pks_list))}
        )
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assert_invalid_pk(response)

        self.assertFalse(Resource.objects.filter(pk__in=pks_list).exists())

    def test_resource_bulk_update(self):
        """
        Using bulk update view logged in user that has enough permissions can
        modify various atributes of multiple resources at one time.
        """
        self.login_alice()

        deployment = self.create_deployment(owner=self.alice)

        resources = []
        for _counter in xrange(3):
            r = self.create_resource(owner=self.alice) 
            r.tags.add('ccc')
            resources.append(r)

        url = reverse('storage:resource_bulk_update')

        data = {
            'records_pks': ",".join(
                [str(resource.pk) for resource in resources] +
                [str(self.TEST_PK)]
            ),
            'tags2add': u'aaaa,bbb',
            'tags2remove': u'ccc',
            'deployment': deployment.pk,
            'status': ResourceStatus.PUBLIC,
            'managers': [self.ziutek.pk]
        }
        response = self.client.post(url, data=data)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

        for resource in resources:
            new_resource = Resource.objects.get(pk=resource.pk)
            self.assertEqual(new_resource.deployment.pk, data['deployment'])
            self.assertEqual(new_resource.status, data['status'])

            self.assertItemsEqual(
                new_resource.tags.values_list('name', flat=True),
                data['tags'].split(',')
            )
            self.assertItemsEqual(
                new_resource.managers.values_list('pk', flat=True),
                data['managers']
            )

    def test_resource_define_prefix(self):
        """
        Using define prefix view logged in user that has enough permissions can
        modify behaviour of resource name of multiple resources at one time.
        """
        self.login_alice()

        deployment = self.create_deployment(owner=self.alice)

        resources = [
            self.create_resource(owner=self.alice, deployment=deployment)
            for _counter in xrange(3)
        ]

        url = reverse('storage:resource_define_prefix')

        data = {
            'pks': ",".join(
                [str(resource.pk) for resource in resources] +
                [str(self.TEST_PK)]
            ),
            'custom_prefix': 'test-prefix',
            'append': 'true'
        }
        response = self.client.post(url, data=data)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

        for resource in resources:
            new_resource = Resource.objects.get(pk=resource.pk)
            self.assertEqual(new_resource.inherit_prefix, True)
            self.assertEqual(new_resource.custom_prefix, data['custom_prefix'])

    def test_resource_generate_thumbnail(self):
        """
        When resource is created and resource file type supports creating
        thumbnail, then thumbnail is created and assigned to `file_thumbnail`
        attribute
        """
        image_file = os.path.join(self.SAMPLE_MEDIA_PATH, 'image_1.jpg')

        with open(image_file) as handler:
            resource = self.create_resource(
                owner=self.alice,
                file_content=handler.read()
            )

            self.assertFalse(resource.file_thumbnail.name)
            resource.update_metadata(commit=True)
            resource.generate_thumbnails()
            self.assertTrue(resource.file_thumbnail.name)
