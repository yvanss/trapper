# -*- coding: utf-8 -*-

import json

from django.core.urlresolvers import reverse

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, LocationTestMixin, DeploymentTestMixin,
)
from trapper.apps.geomap.models import Deployment


class BaseGeomapTestCase(
        ExtendedTestCase,
        LocationTestMixin,
        DeploymentTestMixin
):
    def setUp(self):
        super(BaseGeomapTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()


class AnonymousDeploymentTestCase(BaseGeomapTestCase):
    """Deployment logic for anonymous users"""

    def test_deployment_list(self):
        """Anonymous user can not access list"""
        url = reverse('geomap:deployment_list')
        self.assert_forbidden(url)

    def test_deployment_json(self):
        """Anonymous user can not access API"""
        url = reverse('geomap:api-deployment-list')
        self.assert_forbidden(url)

    def test_deployment_details(self):
        """Anonymous user can not access details"""
        url = reverse(
            'geomap:deployment_detail', kwargs={'pk': 1}
        )
        self.assert_forbidden(url=url)

    def test_deployment_delete(self):
        """Anonymous user has to login before delete."""
        url = reverse('geomap:deployment_delete', kwargs={'pk': 1})
        self.assert_auth_required_json(url=url, method='get')
        self.assert_auth_required_json(url=url, method='post')


class DeploymentTestCase(BaseGeomapTestCase):
    """Deployment permission logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(DeploymentTestCase, self).setUp()
        self.login_alice()

    def test_deployment_list(self):
        """Authenticated user can access to deployment list"""
        url = reverse('geomap:deployment_list')
        self.assert_access_granted(url)

    def test_deployment_json(self):
        """Authenticated user can see accessible deployments"""
        name_public = 'ID_PUBLIC'
        name_private = 'ID_PRIVATE'
        name_private2 = 'ID_PRIVATE_2'

        deployment_public = self.create_deployment(
            owner=self.alice, deployment_code=name_public,
        )
        deployment_private = self.create_deployment(
            owner=self.alice, deployment_code=name_private,
        )
        deployment_private2 = self.create_deployment(
            owner=self.ziutek, deployment_code=name_private2,
        )

        url = reverse('geomap:api-deployment-list')
        response = self.client.get(url)
        content = json.loads(response.content)['results']

        deployment_pk_list = [item['pk'] for item in content]

        self.assertIn(deployment_public.pk, deployment_pk_list, 'Public not shown')
        self.assertIn(
            deployment_private.pk, deployment_pk_list, 'Private not shown'
        )
        self.assertNotIn(
            deployment_private2.pk, deployment_pk_list, 'Private2 shown'
        )

    def test_deployment_delete_owner(self):
        """Owner can delete own deployment. Public status doesn't matter."""
        deployment = self.create_deployment(
            owner=self.alice, deployment_code='ID_1'
        )
        url = reverse('geomap:deployment_delete', kwargs={'pk': deployment.pk})
        redirection = reverse('geomap:deployment_list')
        self.assert_redirect(url, redirection=redirection)

        self.assertFalse(Deployment.objects.filter(pk=deployment.pk).exists())

    def test_deployment_delete_other(self):
        """Authenticated user cannot delete someone else deployment.
        """
        deployment = self.create_deployment(
            owner=self.ziutek, deployment_code='ID_2'
        )
        url = reverse('geomap:deployment_delete', kwargs={'pk': deployment.pk})
        self.assert_forbidden(url)
        self.assertTrue(Deployment.objects.filter(pk=deployment.pk).exists())

    def test_deployment_delete_multiple(self):
        """Owner can delete own deployment using multiple delete.
        """
        deployment_owner = self.create_deployment(
            owner=self.alice, deployment_code='ID_1'
        )
        deployment_other = self.create_deployment(
            owner=self.ziutek, deployment_code='ID_2'
        )

        params = {
            'pks': ",".join([
                str(deployment_owner.pk),
                str(deployment_other.pk),
                str(self.TEST_PK)
            ]),
        }
        url = reverse('geomap:deployment_delete_multiple')
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

        self.assert_invalid_pk(response)
        self.assertFalse(
            Deployment.objects.filter(pk=deployment_owner.pk).exists()
        )
        self.assertTrue(
            Deployment.objects.filter(pk=deployment_other.pk).exists()
        )
