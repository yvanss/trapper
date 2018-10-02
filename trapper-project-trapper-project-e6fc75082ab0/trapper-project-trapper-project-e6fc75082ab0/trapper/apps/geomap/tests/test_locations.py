# -*- coding: utf-8 -*-

import json

from django.core.urlresolvers import reverse

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, LocationTestMixin,
)
from trapper.apps.geomap.models import Location


class BaseGeomapTestCase(ExtendedTestCase, LocationTestMixin):
    def setUp(self):
        super(BaseGeomapTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()


class AnonymousLocationTestCase(BaseGeomapTestCase):
    """Location logic for anonymous users"""

    def test_location_list(self):
        """Anonymous user can access to location list"""
        url = reverse('geomap:location_list')
        self.assert_access_granted(url)

    def test_location_json(self):
        """Anonymous user can see only PUBLIC locations"""
        name_public = 'ID_PUBLIC'
        name_private = 'ID_PRIVATE'

        location_public = self.create_location(
            owner=self.alice, name=name_public, location_id=name_public,
            is_public=True
        )
        location_private = self.create_location(
            owner=self.alice, name=name_private, location_id=name_private,
            is_public=False
        )

        url = reverse('geomap:api-location-list')
        response = self.client.get(url)
        content = json.loads(response.content)['results']

        location_pk_list = [item['pk'] for item in content]

        self.assertIn(location_public.pk, location_pk_list, 'Public not shown')
        self.assertNotIn(
            location_private.pk, location_pk_list, 'Private shown'
        )

    def test_location_delete(self):
        """Anonymous user has to login before delete."""
        url = reverse('geomap:location_delete', kwargs={'pk': 1})
        self.assert_auth_required_json(url=url, method='get')
        self.assert_auth_required_json(url=url, method='post')


class LocationTestCase(BaseGeomapTestCase):
    """Location permission logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(LocationTestCase, self).setUp()
        self.login_alice()

    def test_location_list(self):
        """Authenticated user can access to location list"""
        url = reverse('geomap:location_list')
        self.assert_access_granted(url)

    def test_location_json(self):
        """Authenticated user can see own private resources locations"""
        name_public = 'ID_PUBLIC'
        name_private = 'ID_PRIVATE'
        name_private2 = 'ID_PRIVATE_2'

        location_public = self.create_location(
            owner=self.alice, name=name_public, location_id=name_public,
            is_public=True
        )
        location_private = self.create_location(
            owner=self.alice, name=name_private, location_id=name_private,
            is_public=False
        )
        location_private2 = self.create_location(
            owner=self.ziutek, name=name_private2, location_id=name_private2,
            is_public=False
        )

        url = reverse('geomap:api-location-list')
        response = self.client.get(url)
        content = json.loads(response.content)['results']

        location_pk_list = [item['pk'] for item in content]

        self.assertIn(location_public.pk, location_pk_list, 'Public not shown')
        self.assertIn(
            location_private.pk, location_pk_list, 'Private not shown'
        )
        self.assertNotIn(
            location_private2.pk, location_pk_list, 'Private2 shown'
        )

    def test_location_delete_owner(self):
        """Owner can delete own location. Public status doesn't matter."""
        location = self.create_location(
            owner=self.alice, name='ID_1', location_id='ID_1'
        )
        url = reverse('geomap:location_delete', kwargs={'pk': location.pk})
        redirection = reverse('geomap:location_list')
        self.assert_redirect(url, redirection=redirection)

        self.assertFalse(Location.objects.filter(pk=location.pk).exists())

    def test_location_delete_other(self):
        """Authenticated user cannot delete someone else location. Public
        status doesn't matter"""
        location = self.create_location(
            owner=self.ziutek, name='ID_2', location_id='ID_2'
        )
        url = reverse('geomap:location_delete', kwargs={'pk': location.pk})
        self.assert_forbidden(url)
        self.assertTrue(Location.objects.filter(pk=location.pk).exists())

    def test_location_delete_multiple(self):
        """Owner can delete own location using multiple delete.
        Public status doesn't matter.
        """
        location_owner = self.create_location(
            owner=self.alice, name='ID_1', location_id='ID_1'
        )
        location_other = self.create_location(
            owner=self.ziutek, name='ID_2', location_id='ID_2'
        )

        params = {
            'pks': ",".join([
                str(location_owner.pk),
                str(location_other.pk),
                str(self.TEST_PK)
            ]),
        }
        url = reverse('geomap:location_delete_multiple')
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

        self.assert_invalid_pk(response)
        self.assertFalse(
            Location.objects.filter(pk=location_owner.pk).exists()
        )
        self.assertTrue(
            Location.objects.filter(pk=location_other.pk).exists()
        )
