# -*- coding: utf-8 -*-

import json

from django.core.urlresolvers import reverse
from django.utils.timezone import now

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, ClassificatorTestMixin,
    ResearchProjectTestMixin, ClassificationProjectTestMixin,
    CollectionTestMixin
)
from trapper.apps.media_classification.models import (
    Classificator, Classification
)
from trapper.apps.media_classification.taxonomy import (
    ClassificatorSettings, ClassificationStatus
)


class BaseClassificatorTestCase(
    ExtendedTestCase, ClassificatorTestMixin,
    ResearchProjectTestMixin
):
    def setUp(self):
        super(BaseClassificatorTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

    def get_classificator_details_url(self, classificator):
        return reverse(
            'media_classification:classificator_detail',
            kwargs={'pk': classificator.pk}
        )

    def get_classificator_update_url(self, classificator):
        return reverse(
            'media_classification:classificator_update',
            kwargs={'pk': classificator.pk}
        )

    def get_classificator_delete_url(self, classificator):
        return reverse(
            'media_classification:classificator_delete',
            kwargs={'pk': classificator.pk}
        )

    def get_classificator_clone_url(self, classificator):
        return reverse(
            'media_classification:classificator_clone',
            kwargs={'pk': classificator.pk}
        )

    def get_classificator_list_url(self):
        return reverse('media_classification:classificator_list')


class AnonymousClassificatorTestCase(BaseClassificatorTestCase):
    """Classificator logic for anonymous users"""

    def test_project_list(self):
        """Anonymous user has to login before seeing classificator list"""
        url = reverse('media_classification:classificator_list')
        self.assert_auth_required(url)

    def test_classificator_json(self):
        """Anonymous user cannot see API data"""
        url = reverse('media_classification:api-classificator-list')
        self.assert_forbidden(url)

    def test_details(self):
        """
        Anonymous user has to login before seeing details of classificator
        """
        url = reverse(
            'media_classification:classificator_detail', kwargs={'pk': 1}
        )
        self.assert_auth_required(url=url)

    def test_create(self):
        """Anonymous user has to login before creating classificator"""
        url = reverse('media_classification:classificator_create')
        self.assert_auth_required(url=url)

    def test_delete(self):
        """Anonymous user has to login before delete project"""
        url = reverse(
            'media_classification:classificator_delete', kwargs={'pk': 1}
        )
        self.assert_auth_required_json(url=url, method='get')
        url = reverse('media_classification:classificator_delete_multiple')
        self.assert_auth_required_json(url=url, method='post')

    def test_update(self):
        """Anonymous user has no permissions to update project"""
        url = reverse(
            'media_classification:classificator_update', kwargs={'pk': 1}
        )
        self.assert_forbidden(url=url, method='post')


class ClassificatorPermissionsTestCase(BaseClassificatorTestCase):
    """Classificator permission logic for authenticated users"""

    def setUp(self):
        """Login alice for all tests"""
        super(ClassificatorPermissionsTestCase, self).setUp()
        self.login_alice()

    def test_list(self):
        """Authenticated user can access to classificators list"""

        url = reverse('media_classification:classificator_list')
        self.assert_access_granted(url)

    def test_json(self):
        """Authenticated user can see own projects or projects that user has
        any role"""

        classificator1 = self.create_classificator(owner=self.alice)
        classificator2 = self.create_classificator(owner=self.ziutek)
        url = reverse('media_classification:api-classificator-list')

        response = self.client.get(url)
        content = json.loads(response.content)['results']

        classificator_list = [item['pk'] for item in content]

        self.assertIn(classificator1.pk, classificator_list, 'Own not shown')
        self.assertIn(classificator2.pk, classificator_list, 'Other not shown')

    def test_details_own(self):
        """Authenticated user can view details of own classificator"""
        classificator = self.create_classificator(owner=self.alice)
        url = self.get_classificator_details_url(classificator=classificator)
        self.assert_access_granted(url)

    def test_details_other(self):
        """Authenticated user can view details other users classificator"""
        classificator = self.create_classificator(owner=self.ziutek)
        url = self.get_classificator_details_url(classificator=classificator)
        self.assert_access_granted(url)

    def test_update_own(self):
        """Authenticated user can update own classificator"""
        classificator = self.create_classificator(owner=self.alice)
        url = self.get_classificator_update_url(classificator=classificator)
        params = {'name': 'Updated classificator'}
        self.assert_access_granted(url, method='post', data=params)

    def test_update_other(self):
        """Authenticated user cannot update other user classificators"""
        classificator = self.create_classificator(owner=self.ziutek)
        url = self.get_classificator_update_url(classificator=classificator)
        params = {'name': 'Updated classificator'}
        self.assert_forbidden(url, method='post', data=params)

    def test_delete_own(self):
        """Authenticated user can delete own classificator"""
        classificator = self.create_classificator(owner=self.alice)
        url = self.get_classificator_delete_url(classificator=classificator)
        params = {'pks': classificator.pk}
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

    def test_delete_other(self):
        """Authenticated user cannot delete other user classificators"""
        classificator = self.create_classificator(owner=self.ziutek)
        url = self.get_classificator_delete_url(classificator=classificator)
        params = {'pks': classificator.pk}
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertFalse(status)

    def test_clone_own(self):
        """Authenticated user can clone own classificator"""
        classificator = self.create_classificator(owner=self.alice)
        url = self.get_classificator_clone_url(classificator=classificator)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_clone_other(self):
        """Authenticated user can clone other user classificators"""
        classificator = self.create_classificator(owner=self.ziutek)
        url = self.get_classificator_clone_url(classificator=classificator)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)


class ClassificatorTestCase(
    BaseClassificatorTestCase, ClassificationProjectTestMixin,
    CollectionTestMixin
):
    """Classificator logic for authenticated users"""

    def setUp(self):
        """Login alice for all tests"""
        super(ClassificatorTestCase, self).setUp()
        self.login_alice()

    def test_create(self):
        """Using create classificator view authenticated user can create
        new classificator. Classificator can be created without
        dynamic or static definitions"""
        url = reverse('media_classification:classificator_create')
        name = 'Test classificator'
        params = {
            'classificator-name': name,
            'classificator-template': ClassificatorSettings.TEMPLATE_INLINE
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Classificator.objects.filter(name=name).exists())

    def test_create_only_static(self):
        """Using create classificator view authenticated user can create
        new classificator with static data"""
        url = reverse('media_classification:classificator_create')
        name = 'Test classificator'
        params = {
            'classificator-name': name,
            'classificator-template': ClassificatorSettings.TEMPLATE_INLINE,
            'annotations': 'on',
            'target_annotations': 'S'
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Classificator.objects.filter(name=name).exists())
        classificator = Classificator.objects.get(name=name)

        self.assertItemsEqual(
            classificator.active_predefined_attr_names, ['annotations']
        )

    def test_create_only_dynamic(self):
        """Using create classificator view authenticated user can create
        new classificator with dynamic data"""
        url = reverse('media_classification:classificator_create')
        name = 'Test classificator'
        params = {
            'custom_attrs_manage': True,
            'classificator-name': name,
            'classificator-template': ClassificatorSettings.TEMPLATE_INLINE,
            'name': 'custom attribute',
            'field_type': 'S',
            'description': 'dynamic attr description',
            'target': 'D',

        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Classificator.objects.filter(name=name).exists())
        classificator = Classificator.objects.get(name=name)

        self.assertEqual(
            classificator.dynamic_attrs_order, params['name']
        )

    def test_create_both(self):
        """Using create classificator view authenticated user can create
        new classificator with static and dynamic data"""
        url = reverse('media_classification:classificator_create')
        name = 'Test classificator'
        params = {
            'custom_attrs_manage': True,
            'classificator-name': name,
            'classificator-template': ClassificatorSettings.TEMPLATE_INLINE,
            'name': 'custom attribute',
            'field_type': 'S',
            'description': 'dynamic attr description',
            'target': 'D',
            'annotations': 'on',
            'target_annotations': 'S'

        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Classificator.objects.filter(name=name).exists())
        classificator = Classificator.objects.get(name=name)

        self.assertItemsEqual(
            classificator.active_predefined_attr_names, ['annotations']
        )
        self.assertEqual(
            classificator.dynamic_attrs_order, params['name']
        )

    def test_update(self):
        """Using create classificator view authenticated user that has enough
        permissions can update existing classificator. Base classificator
        parameters can be updated without changing static/dynamic data
        definition"""
        classificator = self.create_classificator(owner=self.alice)
        old_name = classificator.name
        url = self.get_classificator_update_url(classificator=classificator)
        name = 'Updated test classificator'
        params = {
            'classificator-name': name,
            'classificator-template': ClassificatorSettings.TEMPLATE_INLINE
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Classificator.objects.filter(name=name).exists())
        self.assertFalse(Classificator.objects.filter(name=old_name).exists())

    def test_update_static(self):
        """Using create classificator view authenticated user that has enough
        permissions can update existing classificator with static data"""
        predefined_attrs = {
            u'annotations': u'true',
            u'required_annotations': u'false',
            u'target_annotations': u'S',
        }
        static_attrs_order = u'annotations'

        classificator = self.create_classificator(
            owner=self.alice, predefined_attrs=predefined_attrs,
            static_attrs_order=static_attrs_order
        )
        url = self.get_classificator_update_url(classificator=classificator)
        name = 'Updated test classificator'
        params = {
            'classificator-name': name,
            'classificator-template': ClassificatorSettings.TEMPLATE_INLINE,
            'required_annotations': 'on',
            'annotations': 'on',
            'target_annotations': 'D',
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Classificator.objects.filter(name=name).exists())

        classificator = Classificator.objects.get(pk=classificator.pk)
        self.assertEqual(
            classificator.predefined_attrs['target_annotations'],
            params['target_annotations']
        )

    def test_update_dynamic(self):
        """Using create classificator view authenticated user that has enough
        permissions can update existing classificator with dynamic data"""
        custom_attrs = {
            u'New value': (
                u'{"initial": "", "target": "D", "required": true, '
                u'"values": "", "field_type": "S"}'
            ),
        }
        dynamic_attrs_order = 'Age'

        classificator = self.create_classificator(
            owner=self.alice, custom_attrs=custom_attrs,
            dynamic_attrs_order=dynamic_attrs_order
        )
        url = self.get_classificator_update_url(classificator=classificator)
        name = 'Test classificator'
        params = {
            'custom_attrs_manage': True,
            'classificator-name': name,
            'classificator-template': ClassificatorSettings.TEMPLATE_INLINE,
            'name': 'New value',
            'field_type': 'S',
            'description': 'updated dynamic attr description',
            'target': 'D',
            'initial': '',
            'values': '',
            'classificator-dynamic_attrs_order': 'age',
            'classificator-static_attrs_order': '',
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        classificator = Classificator.objects.get(pk=classificator.pk)
        updated_description = classificator.parse_hstore_values(
            'custom_attrs'
        )['New value']['description']

        self.assertEqual(updated_description, params['description'])

    def test_delete(self):
        """Using create classificator view authenticated user that has enough
        permissions can delete existing classificator.
        """
        classificator = self.create_classificator(owner=self.alice)
        url = reverse('media_classification:classificator_delete_multiple')
        params = {'pks': ",".join([str(classificator.pk), str(self.TEST_PK)])}
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assert_invalid_pk(response)
        self.assertFalse(
            Classificator.objects.filter(pk=classificator.pk).exists()
        )

    def test_delete_multiple(self):
        """Using create classificator view authenticated user that has enough
        permissions can delete multiple existing classificators at single
        request"""
        classificator1 = self.create_classificator(owner=self.alice)
        classificator2 = self.create_classificator(owner=self.alice)
        url = reverse('media_classification:classificator_delete_multiple')
        params = {
            'pks': ",".join([str(classificator1.pk), str(classificator2.pk)])
        }
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assertFalse(
            Classificator.objects.filter(
                pk__in=[classificator1.pk, classificator2.pk]
            ).exists()
        )

    def test_delete_approved(self):
        """Using create classificator view authenticated user that has enough
        permissions can delete existing classificator that is connected to
        project with approved classification.

        That classificator is not acutually deleted but instead
        `disabled_at` and `disabled_by` flags are set
        """
        classificator = self.create_classificator(owner=self.alice)

        research_project = self.create_research_project(owner=self.alice)
        project = self.create_classification_project(
            owner=self.alice, research_project=research_project,
            classificator=classificator
        )
        resource = self.create_resource(owner=self.alice)

        collection = self.create_classification_project_collection(
            project=project,
            collection=self.create_research_project_collection(
                project=research_project,
                collection=self.create_collection(
                    owner=self.alice,
                    resources=[resource]
                )
            )
        )
        Classification.objects.create(
            resource=resource,
            project=project,
            collection=collection,
            created_at=now(),
            status=ClassificationStatus.APPROVED,
            approved_by=self.alice,
            approved_at=now()
        )
        url = reverse('media_classification:classificator_delete_multiple')
        params = {'pks': classificator.pk}

        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        classificator = Classificator.objects.get(pk=classificator.pk)

        self.assertTrue(classificator.disabled_at)
        self.assertTrue(classificator.disabled_by)

    def test_clone(self):
        """Using create classificator view authenticated user can clone
        existing classificator with new name.
        New classificator owner is currently logged in user.
        """
        predefined_attrs = {
            u'annotations': u'true',
            u'required_annotations': u'false',
            u'target_annotations': u'S',
        }
        static_attrs_order = u'annotations'

        classificator = self.create_classificator(
            owner=self.ziutek, predefined_attrs=predefined_attrs,
            static_attrs_order=static_attrs_order
        )
        url = reverse(
            'media_classification:classificator_clone',
            kwargs={'pk': classificator.pk}
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        new_name = Classificator.CLONE_PATTERN.format(
            count=1, name=classificator.name
        )

        self.assertTrue(
            Classificator.objects.filter(name=new_name).exists()
        )

        cloned_classificator = Classificator.objects.get(name=new_name)
        self.assertEqual(cloned_classificator.owner, self.alice)

