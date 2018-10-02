# -*- coding: utf-8 -*-

import json
import os
import shutil

from django.core.urlresolvers import reverse
from django.utils.lorem_ipsum import words

from trapper.apps.accounts.utils import get_external_collections_path
from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, CollectionTestMixin,
    ResearchProjectTestMixin
)
from trapper.apps.storage.taxonomy import (
    ResourceStatus, CollectionStatus,
    CollectionMemberLevels
)
from trapper.apps.storage.forms import CollectionRequestForm
from trapper.apps.storage.models import Collection
from trapper.apps.messaging.models import CollectionRequest


class BaseCollectionTestCase(ExtendedTestCase, CollectionTestMixin):
    def setUp(self):
        super(BaseCollectionTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

        self.collection_public = self.create_collection(
            owner=self.alice, status=CollectionStatus.PUBLIC
        )
        self.collection_ondemand = self.create_collection(
            owner=self.alice, status=CollectionStatus.ON_DEMAND
        )
        self.collection_private = self.create_collection(
            owner=self.alice, status=CollectionStatus.PRIVATE
        )

    def get_collection_create_url(self):
        """Default url for creating collection"""
        return reverse('storage:collection_create')

    def get_collection_details_url(self, collection):
        """Default url for details"""
        return reverse(
            'storage:collection_detail', kwargs={'pk': collection.pk}
        )

    def get_collection_update_url(self, collection):
        """Default url for update"""
        return reverse(
            'storage:collection_update', kwargs={'pk': collection.pk}
        )

    def get_collection_delete_url(self, collection):
        """Default url for delete"""
        return reverse(
            'storage:collection_delete', kwargs={'pk': collection.pk}
        )

    def get_collection_request_url(self, collection):
        """Default url for collection permission request"""
        return reverse(
            'storage:collection_request', kwargs={'pk': collection.pk}
        )


class AnonymousCollectionTestCase(BaseCollectionTestCase):
    """Collection logic for anonymous users"""

    def test_collection_list(self):
        """Anonymous user can access to collection list"""
        url = reverse('storage:collection_list')
        self.assert_access_granted(url)

    def test_collection_json(self):
        """Anonymous user can see only PUBLIC resources"""

        url = reverse('storage:api-collection-list')
        response = self.client.get(url)
        content = json.loads(response.content)['results']

        collection_pk_list = [item['pk'] for item in content]

        self.assertIn(
            self.collection_public.pk, collection_pk_list, 'Public not shown'
        )
        self.assertNotIn(
            self.collection_ondemand.pk, collection_pk_list, 'OnDemand shown'
        )
        self.assertNotIn(
            self.collection_private.pk, collection_pk_list, 'Private shown'
        )

    def test_collection_details(self):
        """Anonymous user has no permissions to access non-public details."""
        url_private = self.get_collection_details_url(
            collection=self.collection_private
        )
        url_ondemand = self.get_collection_details_url(
            collection=self.collection_ondemand
        )
        url_public = self.get_collection_details_url(
            collection=self.collection_public
        )
        self.assert_forbidden(url=url_private)
        self.assert_forbidden(url=url_ondemand)
        self.assert_access_granted(url=url_public)

    def test_collection_delete(self):
        """Anonymous user has to login before delete."""
        url = reverse('storage:collection_delete', kwargs={'pk': 1})
        self.assert_auth_required_json(url=url, method='get')
        self.assert_auth_required_json(url=url, method='post')

    def test_collection_delete_multiple(self):
        """Anonymous user has to login before delete.
        Delete is handled by Ajax"""
        url = reverse('storage:collection_delete_multiple')
        self.assert_auth_required_json(url=url, method='post')

    def test_collection_update(self):
        """Anonymous user has no permissions to update."""
        url = reverse('storage:collection_update', kwargs={'pk': 1})
        self.assert_forbidden(url=url, method='post')

    def test_collection_request(self):
        """Anonymous user has to login before requesting access."""
        url = reverse('storage:collection_request', kwargs={'pk': 1})
        self.assert_auth_required(url=url, method='post')

    def test_bulk_update(self):
        """Anonymous user has to login before using bulk update."""
        url = reverse('storage:collection_bulk_update')
        self.assert_auth_required(url=url, method='get')
        self.assert_auth_required(url=url, method='post')

    def test_create_collection(self):
        """Anonymous user has to login before creating collection."""
        url = reverse('storage:collection_create')
        self.assert_auth_required(url=url, method='get')
        self.assert_auth_required(url=url, method='post')

    def test_append_collection(self):
        """Anonymous user has no permissions to append to collection."""
        url = reverse('storage:collection_append')
        self.assert_forbidden(url=url, method='post')


class CollectionPermissionsListTestCase(BaseCollectionTestCase):
    """Collection listing permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(CollectionPermissionsListTestCase, self).setUp()
        self.login_alice()

    def test_collection_list(self):
        """Logged in user can access collection lisst"""
        url = reverse('storage:collection_list')
        self.assert_access_granted(url)

    def test_collection_json(self):
        """Logged in user can see

        * PUBLIC collections
        * OnDemand collections even if user has no access to view details
        * Own PRIVATE collections

        User cannot see other's people PRIVATE collections
        """
        url = reverse('storage:api-collection-list')
        self.collection_private_ziutek = self.create_collection(
            owner=self.ziutek, status=CollectionStatus.PRIVATE
        )

        response = self.client.get(url)
        content = json.loads(response.content)['results']
        collection_pk_list = [item['pk'] for item in content]

        self.assertIn(
            self.collection_public.pk, collection_pk_list, 'Public not shown'
        )
        self.assertIn(
            self.collection_ondemand.pk, collection_pk_list,
            'OnDemand not shown'
        )
        self.assertIn(
            self.collection_private.pk, collection_pk_list,
            'Private not shown (own)'
        )
        self.assertNotIn(
            self.collection_private_ziutek.pk, collection_pk_list,
            'Private not shown (ziutek)'
        )


class CollectionPermissionsDetailsTestCase(BaseCollectionTestCase):
    """Details permission logic for logged in user"""

    def test_details_owner(self):
        """Collection owner can access details"""
        self.login_alice()
        collection = self.create_collection(owner=self.alice)
        url = self.get_collection_details_url(collection=collection)
        self.assert_access_granted(url)

    def test_details_manager(self):
        """Collection manager can access details"""
        self.login_alice()
        collection = self.create_collection(
            owner=self.ziutek, managers=[self.alice]
        )

        url = self.get_collection_details_url(collection=collection)
        self.assert_access_granted(url)

    def test_details_role_access(self):
        """CollectionMember with access level can access details"""
        self.login_alice()
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS)]
        )
        url = self.get_collection_details_url(collection=collection)
        self.assert_access_granted(url)

    def test_details_role_update(self):
        """CollectionMember with update level is forbidden to access details"""
        self.login_alice()
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.UPDATE)]
        )
        url = self.get_collection_details_url(collection=collection)
        self.assert_forbidden(url)

    def test_details_role_delete(self):
        """CollectionMember with delete level is forbidden to access details"""
        self.login_alice()
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.DELETE)]
        )
        url = self.get_collection_details_url(collection=collection)
        self.assert_forbidden(url)

    def test_details_role_access_basic(self):
        """CollectionMember with basic access can access details"""
        self.login_alice()
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS_BASIC)]
        )
        url = self.get_collection_details_url(collection=collection)
        self.assert_access_granted(url)

    def test_details_no_roles(self):
        """User without any roles, and is not manager or owner cannot access
        details"""
        self.login_alice()
        collection = self.create_collection(
            owner=self.ziutek,
        )
        url = self.get_collection_details_url(collection=collection)
        self.assert_forbidden(url)

    def test_list_resources_allowed(self):
        """If user has enough access, he can see resources assigned to
        particular collection through api"""
        self.login_alice()

        resource_public = self.create_resource(
            owner=self.alice, status=ResourceStatus.PUBLIC
        )
        resource_ondemand = self.create_resource(
            owner=self.alice, status=ResourceStatus.ON_DEMAND
        )
        resource_private = self.create_resource(
            owner=self.alice, status=ResourceStatus.PRIVATE
        )

        collection = self.create_collection(
            owner=self.alice,
            resources=[resource_private, resource_ondemand, resource_public]
        )

        url = u'{url}?collections={collection}'.format(
            url=reverse('storage:api-resource-list'),
            collection=collection.pk
        )
        response = self.assert_access_granted(url)
        self.assertEqual(len(json.loads(response.content)['results']), 3)

    def test_list_resources_forbidden(self):
        """If user has not enough access, resource api should return
        only records that are available to everyone"""
        self.login_ziutek()

        resource_public = self.create_resource(
            owner=self.alice, status=ResourceStatus.PUBLIC
        )
        resource_ondemand = self.create_resource(
            owner=self.alice, status=ResourceStatus.ON_DEMAND
        )
        resource_private = self.create_resource(
            owner=self.alice, status=ResourceStatus.PRIVATE
        )

        collection = self.create_collection(
            owner=self.alice,
            resources=[resource_private, resource_ondemand, resource_public],
            status=CollectionStatus.PUBLIC
        )

        url = u'{url}?collections={collection}'.format(
            url=reverse('storage:api-resource-list'),
            collection=collection.pk
        )
        response = self.assert_access_granted(url)
        # Private resource is exluded
        self.assertEqual(len(json.loads(response.content)['results']), 2)


class CollectionPermissionsUpdateTestCase(BaseCollectionTestCase):
    """Update collection permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(CollectionPermissionsUpdateTestCase, self).setUp()
        self.login_alice()

    def test_get_update_owner(self):
        """Resource owner can update resource"""
        collection = self.create_collection(owner=self.alice)
        url = self.get_collection_update_url(collection=collection)
        self.assert_access_granted(url, method='post', data={'name': 'test'})

    def test_get_update_manager(self):
        """Collection manager can update collection"""
        collection = self.create_collection(
            owner=self.ziutek, managers=[self.alice]
        )
        url = self.get_collection_update_url(collection=collection)
        self.assert_access_granted(url, method='post', data={'name': 'test'})

    def test_get_update_role_access(self):
        """CollectionMember with access level cannot update ollection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS)]
        )
        url = self.get_collection_update_url(collection=collection)
        self.assert_forbidden(url, method='post', data={'name': 'test'})

    def test_get_update_role_update(self):
        """CollectionMember with update level can update collection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.UPDATE)]
        )
        url = self.get_collection_update_url(collection=collection)
        self.assert_access_granted(url, method='post', data={'name': 'test'})

    def test_get_update_role_delete(self):
        """CollectionMember with delete level cannot update collection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.DELETE)]
        )
        url = self.get_collection_update_url(collection=collection)
        self.assert_forbidden(url, method='post', data={'name': 'test'})

    def test_get_update_role_access_basic(self):
        """CollectionMember with basic access level cannot update collection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS_BASIC)]
        )
        url = self.get_collection_update_url(collection=collection)
        self.assert_forbidden(url, method='post', data={'name': 'test'})

    def test_get_update_no_roles(self):
        """User without any roles, and is not manager or owner cannot update
        collection"""
        collection = self.create_collection(owner=self.ziutek)
        url = self.get_collection_update_url(collection=collection)
        self.assert_forbidden(url, method='post', data={'name': 'test'})


class CollectionPermissionsDeleteTestCase(BaseCollectionTestCase):
    """
    Delete collection permission logic for logged in user

    .. note::
        Delete multiple uses the same permission logic
    """
    def setUp(self):
        """Login alice by default for all tests and prepare default
        redirection url"""
        super(CollectionPermissionsDeleteTestCase, self).setUp()
        self.login_alice()
        self.redirection = reverse('storage:collection_list')

    def test_delete_owner(self):
        """Collection owner can delete collection"""
        collection = self.create_collection(owner=self.alice)
        url = self.get_collection_delete_url(collection=collection)
        self.assert_redirect(url, self.redirection)

    def test_delete_manager(self):
        """Collection manager can delete collection"""
        collection = self.create_collection(
            owner=self.ziutek, managers=[self.alice]
        )
        url = self.get_collection_delete_url(collection=collection)
        self.assert_redirect(url, self.redirection)

    def test_delete_role_access(self):
        """CollectionMember with access level cannot delete collection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS)]
        )
        url = self.get_collection_delete_url(collection=collection)
        self.assert_forbidden(url)

    def test_delete_role_update(self):
        """CollectionMember with update level cannot delete collection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.UPDATE)]
        )
        url = self.get_collection_delete_url(collection=collection)
        self.assert_forbidden(url)

    def test_delete_role_delete(self):
        """CollectionMember with delete level can delete collection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.DELETE)]
        )
        url = self.get_collection_delete_url(collection=collection)
        self.assert_redirect(url, self.redirection)

    def test_delete_role_access_basic(self):
        """CollectionMember with basic access level cannot delete collection"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS_BASIC)]
        )
        url = self.get_collection_delete_url(collection=collection)
        self.assert_forbidden(url)

    def test_delete_no_roles(self):
        """User without any roles, and is not manager or owner cannot delete
        collection"""
        collection = self.create_collection(owner=self.ziutek,)
        url = self.get_collection_delete_url(collection=collection)
        self.assert_forbidden(url)


class CollectionPermissionsAskAccessTestCase(BaseCollectionTestCase):
    """Ask for collection access permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests and prepare default
        redirection url"""
        super(CollectionPermissionsAskAccessTestCase, self).setUp()
        self.login_alice()
        self.redirection = reverse('storage:collection_list')

    def test_ask_owner(self):
        """There is no point to ask for own collection"""
        collection = self.create_collection(owner=self.alice)
        url = self.get_collection_request_url(collection=collection)
        response = self.assert_access_granted(url)
        self.assertTrue(
            self.assert_context_variable(response, 'already_approved')
        )

    def test_ask_manager(self):
        """There is no point to ask for access to collection where user is
        manager"""
        collection = self.create_collection(
            owner=self.ziutek, managers=[self.alice]
        )
        url = self.get_collection_request_url(collection=collection)
        response = self.assert_access_granted(url)
        self.assertTrue(
            self.assert_context_variable(response, 'already_approved')
        )

    def test_ask_role_access(self):
        """There is no point to ask for access to collection if access is
        already granted"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS)]
        )
        url = self.get_collection_request_url(collection=collection)
        response = self.assert_access_granted(url)
        self.assertTrue(
            self.assert_context_variable(response, 'already_approved')
        )

    def test_ask_role_update(self):
        """If user has update role, it's still possible to ask for permissions
        since this role won't give detail access"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.UPDATE)]
        )
        url = self.get_collection_request_url(collection=collection)
        response = self.assert_access_granted(url)
        form = self.assert_context_variable(response, 'form')
        self.assertTrue(isinstance(form, CollectionRequestForm))

    def test_ask_role_delete(self):
        """If user has delete role, it's still possible to ask for permissions
        since this role won't give detail access"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.DELETE)]
        )
        url = self.get_collection_request_url(collection=collection)
        response = self.assert_access_granted(url)
        form = self.assert_context_variable(response, 'form')
        self.assertTrue(isinstance(form, CollectionRequestForm))

    def test_ask_role_access_basic(self):
        """If user has basic access he can ask for permissions"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS_BASIC)]
        )
        url = self.get_collection_request_url(collection=collection)
        response = self.assert_access_granted(url)
        form = self.assert_context_variable(response, 'form')
        self.assertTrue(isinstance(form, CollectionRequestForm))

    def test_ask_no_roles(self):
        """User without any roles, and is not manager or owner can ask for
        permissions"""
        collection = self.create_collection(owner=self.ziutek)
        url = self.get_collection_request_url(collection=collection)
        response = self.assert_access_granted(url)
        form = self.assert_context_variable(response, 'form')
        self.assertTrue(isinstance(form, CollectionRequestForm))


class CollectionPermissionsBulkUpdateTestCase(BaseCollectionTestCase):
    """Bulk update permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests and prepare default
        redirection url"""
        super(CollectionPermissionsBulkUpdateTestCase, self).setUp()
        self.login_alice()
        self.redirection = reverse('storage:collection_list')

    def _call_helper(self, collection):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        url = reverse('storage:collection_bulk_update')

        data = {
            'pks': [collection.pk],
            'status': CollectionStatus.PUBLIC
        }
        response = self.assert_access_granted(url, method='post', data=data)
        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_bulk_update_owner(self):
        """Owner can perform bulk update operation on collections"""
        collection = self.create_collection(owner=self.alice)
        status = self._call_helper(collection=collection)
        self.assertTrue(status)

    def test_bulk_update_manager(self):
        """Manager can perform bulk operation on collections"""
        collection = self.create_collection(
            owner=self.ziutek, managers=[self.alice]
        )
        status = self._call_helper(collection=collection)
        self.assertTrue(status)

    def test_bulk_update_role_access(self):
        """
        ACCESS role is not enogugh to perform bulk update operation on
        collections
        """
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS)]
        )
        status = self._call_helper(collection=collection)
        self.assertFalse(status)

    def test_bulk_update_role_update(self):
        """UPDATE role is enogugh to perform bulk update operation on
        collections"""
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.UPDATE)]
        )
        status = self._call_helper(collection=collection)
        self.assertTrue(status)

    def test_bulk_update_role_delete(self):
        """
        DELETE role is not enogugh to perform bulk update operation on
        collections
        """
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.DELETE)]
        )
        status = self._call_helper(collection=collection)
        self.assertFalse(status)

    def test_bulk_update_role_access_basic(self):
        """
        BASIC ACCESS status is not enogugh to perform bulk update operation on
        collections
        """
        collection = self.create_collection(
            owner=self.ziutek,
            roles=[(self.alice, CollectionMemberLevels.ACCESS_BASIC)]
        )
        status = self._call_helper(collection=collection)
        self.assertFalse(status)

    def test_bulk_update_no_roles(self):
        """User without any roles, and is not manager or owner cannot perform
        bulk update operation on collections"""
        collection = self.create_collection(owner=self.ziutek)
        status = self._call_helper(collection=collection)
        self.assertFalse(status)


class CollectionTestCase(BaseCollectionTestCase, ResearchProjectTestMixin):
    """Tests related to modifying data for collection by performing various
    accions"""

    def test_collection_create(self):
        """
        Using create view create storage.Collection model instance
        """

        resources = [
            self.create_resource(owner=self.alice) for _counter in xrange(3)
        ]
        resources_pk = [resource.pk for resource in resources]

        url = reverse('storage:collection_create')
        self.login_alice()
        name = words(count=5, common=False)

        params = {
            'name': name,
            'status': CollectionStatus.PRIVATE,
            'resources': resources_pk
        }
        response = self.client.post(url, params)

        self.assertEqual(response.status_code, 200, response.status_code)
        success = self.assert_json_context_variable(
            response, variable='success'
        )
        self.assertTrue(success)

        self.assertTrue(
            Collection.objects.filter(
                name=name,
                status=CollectionStatus.PRIVATE,
            ).exists()
        )
        self.assertItemsEqual(
            Collection.objects.get(
                name=name, status=CollectionStatus.PRIVATE
            ).resources.values_list('pk', flat=True),
            resources_pk
        )

    def test_collection_append(self):
        """
        Using append collection view, alter existing collection by adding
        additional resource
        """

        resource = self.create_resource(owner=self.alice)
        resource_append = self.create_resource(owner=self.alice)
        resource_append2 = self.create_resource(owner=self.alice)

        collection = self.create_collection(
            owner=self.alice, resources=[resource]
        )

        url = reverse('storage:collection_append')
        detail_url = reverse(
            'storage:collection_detail', kwargs={'pk': collection.pk}
        )
        self.login_alice()

        params = {
            'collection': collection.pk,
            'resources': ",".join(
                [str(resource_append.pk), str(resource_append2.pk)]
            )
        }

        self.assert_redirect(
            url, redirection=detail_url, method='post', data=params
        )

        resource_pks = Collection.objects.get(
            pk=collection.pk
        ).resources.values_list('pk', flat=True)

        self.assertItemsEqual(
            resource_pks,
            sorted([resource.pk, resource_append.pk, resource_append2.pk])
        )

    def test_collection_update(self):
        """
        Using update view logged in user that has enough permissions can
        change existing collection.
        """
        self.login_alice()
        collection = self.create_collection(
            owner=self.alice, status=CollectionStatus.PRIVATE
        )

        url = reverse(
            'storage:collection_update', kwargs={'pk': collection.pk}
        )

        attributes = {
            'name': 'test_name',
            'status': CollectionStatus.PUBLIC,
        }
        self.client.post(url, attributes)

        new_collection = Collection.objects.get(pk=collection.pk)

        self.assertEqual(new_collection.name, attributes['name'])
        self.assertEqual(new_collection.status, attributes['status'])

    def test_collection_delete(self):
        """
        Using delete view logged in user that has enough permissions can
        delete existing collection using GET.
        """
        self.login_alice()
        collection = self.create_collection(
            owner=self.alice, status=CollectionStatus.PRIVATE
        )

        url = reverse(
            'storage:collection_delete', kwargs={'pk': collection.pk}
        )

        self.client.get(url)
        self.assertFalse(Collection.objects.filter(pk=collection.pk).exists())

    def test_collection_delete_multiple(self):
        """
        Using delete view logged in user that has enough permissions can
        delete multiple collections using POST.
        """
        self.login_alice()
        collection1 = self.create_collection(
            owner=self.alice, status=CollectionStatus.PRIVATE
        )
        collection2 = self.create_collection(
            owner=self.alice, status=CollectionStatus.PRIVATE
        )

        url = reverse('storage:collection_delete_multiple')

        pks_list = [collection1.pk, collection2.pk, self.TEST_PK]

        response = self.client.post(
            url, data={'pks': ",".join(map(str, pks_list))}
        )
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assert_invalid_pk(response)

        self.assertFalse(Collection.objects.filter(pk__in=pks_list).exists())

    def test_collection_ask_permissions(self):
        """
        Using ask permissions view logged in user that ask for access to other
        OnDemand collection that user has no access yet.
        """
        self.login_alice()
        collection = self.create_collection(owner=self.ziutek)
        research_project = self.create_research_project(owner=self.alice)

        url = reverse(
            'storage:collection_request', kwargs={'pk': collection.pk}
        )

        self.client.post(
            url,
            data={
                'text': 'Test',
                'object_pk': collection.pk,
                'project': research_project.pk
            }
        )

        self.assertTrue(
            CollectionRequest.objects.filter(
                user=self.ziutek,
                user_from=self.alice,
                collections=collection,
                project=research_project,
            )
        )

    def test_collection_bulk_update(self):
        """
        Using bulk update view logged in user that has enough permissions can
        modify various atributes of multiple collections at one time.
        """
        self.login_alice()

        collections = [
            self.create_collection(owner=self.alice) for _counter in xrange(3)
        ]

        url = reverse('storage:collection_bulk_update')

        data = {
            'pks': ",".join(
                [str(collection.pk) for collection in collections] +
                [str(self.TEST_PK)]
            ),
            'status': CollectionStatus.PUBLIC,
        }
        response = self.client.post(url, data=data)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

        for collection in collections:
            new_collection = Collection.objects.get(pk=collection.pk)
            self.assertEqual(new_collection.status, data['status'])

    def test_dashboard_collections(self):
        """Logged in user in dashboard can see list of own collections.
        Other users collections are exluded"""

        self.login_alice()
        self.create_collection(owner=self.ziutek)
        url = reverse('accounts:dashboard')
        response = self.assert_access_granted(url)
        collections = self.assert_context_variable(response, 'collections')
        self.assertEqual(collections.count(), 3)

    # def test_collection_upload(self):
    #     """
    #     Logged in user can upload yaml config and then collection data
    #     archive to speed up process of creating collections.
    #     This is done in two steps: config -> data. After that collections
    #     defined in yaml config are created.

    #     This test uses upload file method
    #     """

    #     self.create_location(owner=self.alice, location_id='GXS1L1')
    #     self.create_research_project(owner=self.alice, name='ResearchProject1')

    #     definition_file = os.path.join(
    #         self.TEST_DATA_PATH, 'test_definition.yaml'
    #     )
    #     data_file = os.path.join(
    #         self.TEST_DATA_PATH, 'test_archive_small.zip'
    #     )
    #     url = reverse('storage:collection_upload')
    #     redirection_url = reverse('storage:collection_upload_done')

    #     self.login_alice()
    #     with open(definition_file) as definition_handler:
    #         params = {
    #             'collection_upload_wizard_view-current_step': 0,
    #             '0-definition_file': definition_handler,
    #         }
    #         self.assert_access_granted(
    #             url, method='post', data=params
    #         )

    #     with open(data_file) as data_handler:
    #         params = {
    #             'collection_upload_wizard_view-current_step': 1,
    #             '1-archive_file': data_handler,
    #         }
    #         self.assert_redirect(
    #             url, redirection=redirection_url,
    #             method='post', data=params
    #         )

    #     self.assertTrue(
    #         Collection.objects.filter(name='CollectionOne').exists()
    #     )
    #     self.assertTrue(
    #         Collection.objects.filter(name='CollectionTwo').exists()
    #     )

    # def test_collection_upload_preselected(self):
    #     """
    #     Logged in user can upload yaml config and then collection data
    #     archive to speed up process of creating collections.
    #     This is done in two steps: config -> data. After that collections
    #     defined in yaml config are created.

    #     This test uses preselected data file
    #     """
    #     self.login_alice()

    #     self.create_location(owner=self.alice, location_id='GXS1L1')
    #     self.create_research_project(owner=self.alice, name='ResearchProject1')

    #     data_file_name = 'test_archive_small.zip'

    #     definition_file = os.path.join(
    #         self.TEST_DATA_PATH, 'test_definition.yaml'
    #     )
    #     data_file = os.path.join(self.TEST_DATA_PATH, data_file_name)

    #     temp_file = get_external_collections_path(
    #         self.alice.username, data_file_name
    #     )

    #     shutil.copyfile(data_file, temp_file)

    #     url = reverse('storage:collection_upload')
    #     redirection_url = reverse('storage:collection_upload_done')

    #     with open(definition_file) as definition_handler:
    #         params = {
    #             'collection_upload_wizard_view-current_step': 0,
    #             '0-definition_file': definition_handler,
    #             }
    #         self.assert_access_granted(
    #             url, method='post', data=params
    #         )

    #         params = {
    #             'collection_upload_wizard_view-current_step': 1,
    #             '1-uploaded_media': data_file_name,
    #         }
    #         self.assert_redirect(
    #             url, redirection=redirection_url,
    #             method='post', data=params
    #         )

    #     self.assertTrue(
    #         Collection.objects.filter(name='CollectionOne').exists()
    #     )
    #     self.assertTrue(
    #         Collection.objects.filter(name='CollectionTwo').exists()
    #     )
