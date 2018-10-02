# -*- coding: utf-8 -*-

import json

from django.core.urlresolvers import reverse
from django.utils.timezone import now

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, ClassificationProjectTestMixin,
    ResearchProjectTestMixin, CollectionTestMixin
)
from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectRoleLevels, ClassificationProjectStatus,
    ClassificationStatus
)
from trapper.apps.media_classification.models import (
    ClassificationProject, ClassificationProjectRole,
    ClassificationProjectCollection, Classification
)


class BaseClassificationProjectTestCase(
    ExtendedTestCase, ClassificationProjectTestMixin,
    ResearchProjectTestMixin
):
    def setUp(self):
        super(BaseClassificationProjectTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

    def get_classification_project_details_url(self, project):
        return reverse(
            'media_classification:project_detail', kwargs={'pk': project.pk}
        )

    def get_classification_project_update_url(self, project):
        return reverse(
            'media_classification:project_update', kwargs={'pk': project.pk}
        )

    def get_classification_project_delete_url(self, project):
        return reverse(
            'media_classification:project_delete', kwargs={'pk': project.pk}
        )

    def get_classification_project_collection_url(self, collection):
        return reverse(
            'media_classification:project_collection_delete',
            kwargs={'pk': collection.pk}
        )

    def get_classification_project_list_url(self):
        return reverse('media_classification:project_list')


class AnonymousResearchTestCase(BaseClassificationProjectTestCase):
    """Classification project logic for anonymous users"""

    def test_project_list(self):
        """Anonymous user cannot access to classification projects list"""
        url = reverse('media_classification:project_list')
        self.assert_auth_required(url)

    def test_project_json(self):
        """Anonymous user can cannot see projects"""
        url = reverse('media_classification:api-classification-project-list')
        self.assert_forbidden(url)

    def test_details(self):
        """Anonymous user has to login before seeing details of project"""
        url = reverse('media_classification:project_detail', kwargs={'pk': 1})
        self.assert_auth_required(url=url)

    def test_create(self):
        """Anonymous user has to login before creating project"""
        url = reverse('media_classification:project_create')
        self.assert_auth_required(url=url)

    def test_delete(self):
        """Anonymous user has to login before delete project"""
        url = reverse('media_classification:project_delete', kwargs={'pk': 1})
        self.assert_auth_required_json(url=url, method='get')
        url = reverse('media_classification:project_delete_multiple')
        self.assert_auth_required_json(url=url, method='post')

    def test_update(self):
        """Anonymous user has no permissions to update project"""
        url = reverse('media_classification:project_update', kwargs={'pk': 1})
        self.assert_auth_required(url=url, method='post')

    def test_add_collection(self):
        """
        Anonymous user has no permissions to add collection to project
        """
        url = reverse('media_classification:project_collection_add')
        self.assert_forbidden(url)

    def test_remove_collection(self):
        """
        Anonymous user has no permissions to remove collection from project
        """
        url = reverse(
            'media_classification:project_collection_delete', kwargs={'pk': 1}
        )
        self.assert_auth_required_json(url=url, method='get')
        url = reverse(
            'media_classification:project_collection_delete_multiple'
        )
        self.assert_auth_required_json(url=url, method='post')


class ClassificationPermissionsListTestCase(BaseClassificationProjectTestCase):
    """Classification project list permission logic for authenticated users"""

    def test_project_list(self):
        """Authenticated user can access to classification projects list"""

        self.login_alice()
        url = reverse('media_classification:project_list')
        self.assert_access_granted(url)

    def test_project_json(self):
        """Authenticated user can see own projects or projects that user has
        any role"""

        self.login_alice()
        research_project = self.create_research_project(owner=self.alice)
        url = reverse(
            'media_classification:api-classification-project-list'
        )

        project_own = self.create_classification_project(
            owner=self.alice, research_project=research_project,
            enable_crowdsourcing=False

        )
        project_other = self.create_classification_project(
            owner=self.ziutek, research_project=research_project,
            enable_crowdsourcing=False
        )

        response = self.client.get(url)
        content = json.loads(response.content)['results']

        project_pk_list = [item['pk'] for item in content]

        self.assertIn(project_own.pk, project_pk_list, 'Own not shown')
        self.assertNotIn(project_other.pk, project_pk_list, 'Other shown')


class ClassificationPermissionsDetailsTestCase(
    BaseClassificationProjectTestCase, CollectionTestMixin
):
    """Details permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationPermissionsDetailsTestCase, self).setUp()
        self.login_alice()
        self.research_project = self.create_research_project(owner=self.alice)

    def test_details_owner(self):
        """Project owner can access details"""
        project = self.create_classification_project(
            owner=self.alice, research_project=self.research_project
        )

        url = self.get_classification_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_role_admin(self):
        """User with `Admin` role can access details"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        )
        url = self.get_classification_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_role_expert(self):
        """User with `Expert` role can access details"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        )
        url = self.get_classification_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_role_collaborator(self):
        """User with `Collaborator` role can access details"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        )
        url = self.get_classification_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_no_roles(self):
        """User without any role cannot see details"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
        )
        url = self.get_classification_project_details_url(project=project)
        self.assert_auth_required(url)

    def test_list_collections_allowed(self):
        """If user has enough permissions to view project details,
        he can see collections assigned to particular project through api"""
        self.login_alice()

        project = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project

        )

        self.create_classification_project_collection(
            project=project,
            collection=self.create_research_project_collection(
                project=self.research_project,
                collection=self.create_collection(owner=self.alice)
            )
        )
        list_url = reverse(
            'media_classification:api-classification-project-collection-list'
        )
        url = u'{url}?project={pk}'.format(url=list_url, pk=project.pk)
        response = self.assert_access_granted(url)
        self.assertEqual(len(json.loads(response.content)['results']), 1)

    def test_list_collections_forbidden(self):
        """If user has not enough permissions to view project details,
        he cannot see collections assigned to particular project through api"""
        self.login_ziutek()

        project = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project
        )

        self.create_classification_project_collection(
            project=project,
            collection=self.create_research_project_collection(
                project=self.research_project,
                collection=self.create_collection(owner=self.alice)
            )
        )
        list_url = reverse(
            'media_classification:api-classification-project-collection-list'
        )
        url = u'{url}?project={pk}'.format(url=list_url, pk=project.pk)
        response = self.assert_access_granted(url)
        self.assertEqual(len(json.loads(response.content)['results']), 0)


class ClassificationPermissionsUpdateTestCase(
    BaseClassificationProjectTestCase
):
    """Update permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests and prepare default params"""
        super(ClassificationPermissionsUpdateTestCase, self).setUp()
        self.login_alice()
        self.research_project = self.create_research_project(owner=self.alice)
        self.params = {
            'name': 'test-project',
            'classification_project_roles-TOTAL_FORMS': 0,
            'classification_project_roles-INITIAL_FORMS': 0,
            'classification_project_roles-MAX_NUM_FORMS': 1000,
            'classification_project_collections-TOTAL_FORMS': 0,
            'classification_project_collections-INITIAL_FORMS': 0,
            'classification_project_collections-MAX_NUM_FORMS': 1000,
            'status': ClassificationProjectStatus.ONGOING,
            'research_project': self.research_project.pk,
        }

    def test_update_owner(self):
        """Project owner can update project"""
        project = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project,
        )
        url = self.get_classification_project_update_url(project=project)
        redirection = self.get_classification_project_details_url(
            project=project
        )
        self.assert_redirect(url, redirection, method='post', data=self.params)

    def test_update_role_admin(self):
        """User with `Admin` role can update project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        )
        url = self.get_classification_project_update_url(project=project)
        redirection = self.get_classification_project_details_url(
            project=project
        )
        self.assert_redirect(url, redirection, method='post', data=self.params)

    def test_update_role_expert(self):
        """User with `Expert` role cannot update project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        )
        url = self.get_classification_project_update_url(project=project)

        self.assert_auth_required(url, method='post', data=self.params)

    def test_update_role_collaborator(self):
        """User with `Collaborator` role cannot update project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        )
        url = self.get_classification_project_update_url(project=project)
        self.assert_auth_required(url, method='post', data=self.params)

    def test_update_no_roles(self):
        """User without any role cannot update project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
        )
        url = self.get_classification_project_update_url(project=project)
        self.assert_auth_required(url, method='post', data=self.params)


class ClassificationPermissionsDeleteTestCase(
    BaseClassificationProjectTestCase
):
    """
    Delete permission logic for logged in user

    .. note::
        Delete multiple uses the same permission logic
    """

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationPermissionsDeleteTestCase, self).setUp()
        self.research_project = self.create_research_project(owner=self.alice)
        self.login_alice()

    def test_delete_owner(self):
        """Project owner can delete project"""
        project = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project,
        )
        url = self.get_classification_project_delete_url(project=project)
        redirection = self.get_classification_project_list_url()
        self.assert_redirect(url, redirection)

    def test_delete_role_admin(self):
        """User with `Admin` role can delete project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        )
        url = self.get_classification_project_delete_url(project=project)
        redirection = self.get_classification_project_list_url()
        self.assert_redirect(url, redirection)

    def test_delete_role_expert(self):
        """User with `Expert` role cannot delete project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        )
        url = self.get_classification_project_delete_url(project=project)

        self.assert_forbidden(url)

    def test_delete_role_collaborator(self):
        """User with `Collaborator` role cannot delete project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        )
        url = self.get_classification_project_delete_url(project=project)
        self.assert_forbidden(url)

    def test_delete_no_roles(self):
        """User without any role cannot delete project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
        )
        url = self.get_classification_project_delete_url(project=project)
        self.assert_forbidden(url)


class ClassificationPermissionsCollectionAddTestCase(
    BaseClassificationProjectTestCase, CollectionTestMixin
):
    """
    Add classification project collection permission logic for logged in user
    """

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationPermissionsCollectionAddTestCase, self).setUp()
        self.research_project = self.create_research_project(owner=self.alice)

        self.collection = self.create_research_project_collection(
            project=self.research_project,
            collection=self.create_collection(self.alice)
        )
        self.login_alice()

    def _call_helper(self, project):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        pdata which is json"""
        params = {
            'classification_project': project.pk,
            'pks': self.collection.pk
        }

        url = reverse('media_classification:project_collection_add')
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_action_owner(self):
        """Project owner can add collection to project"""
        project = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project,
        )
        self.assertTrue(self._call_helper(project))

    def test_action_role_admin(self):
        """User with `Admin` role can add collection to project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        )
        self.assertTrue(self._call_helper(project))

    def test_action_role_expert(self):
        """User with `Expert` role cannot add collection to project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        )
        self.assertFalse(self._call_helper(project))

    def test_action_role_collaborator(self):
        """
        User with `Collaborator` role cannot add collection to project
        """
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        )
        self.assertFalse(self._call_helper(project))

    def test_action_no_roles(self):
        """User without any role cannot add collection to project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
        )
        self.assertFalse(self._call_helper(project))


class ClassificationPermissionsCollectionDeleteTestCase(
    BaseClassificationProjectTestCase, CollectionTestMixin
):
    """
    Delete single classification project collection permission logic for
    logged in user
    """

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationPermissionsCollectionDeleteTestCase, self).setUp()
        self.research_project = self.create_research_project(owner=self.alice)
        self.collection = self.create_collection(owner=self.alice)
        self.research_project_collection = \
            self.create_research_project_collection(
                project=self.research_project,
                collection=self.collection
            )
        self.redirection = self.get_classification_project_list_url()

        self.login_alice()

    def _get_collection(self, project):
        """Build classification project collection based on classification
        project"""
        return self.create_classification_project_collection(
            project=project,
            collection=self.research_project_collection
        )

    def test_action_owner(self):
        """Project owner can delete collection from project"""
        project = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project,
        )
        url = self.get_classification_project_collection_url(
            collection=self._get_collection(project=project)
        )
        self.assert_redirect(url, self.redirection)

    def test_action_role_admin(self):
        """User with `Admin` role can delete collection from project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        )
        url = self.get_classification_project_collection_url(
            collection=self._get_collection(project=project)
        )
        self.assert_redirect(url, self.redirection)

    def test_action_role_expert(self):
        """User with `Expert` role cannot delete collection from project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        )
        url = self.get_classification_project_collection_url(
            collection=self._get_collection(project=project)
        )
        self.assert_forbidden(url)

    def test_action_role_collaborator(self):
        """
        User with `Collaborator` role cannot delete collection from project
        """
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        )
        url = self.get_classification_project_collection_url(
            collection=self._get_collection(project=project)
        )
        self.assert_forbidden(url)

    def test_action_no_roles(self):
        """User without any role cannot delete collection from project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
        )
        url = self.get_classification_project_collection_url(
            collection=self._get_collection(project=project)
        )
        self.assert_forbidden(url)


class ClassificationPermissionsCollectionRemoveMultipleTestCase(
    BaseClassificationProjectTestCase, CollectionTestMixin
):
    """
    Delete multiple classification project collections permission logic for
    logged in user
    """

    def setUp(self):
        """Login alice by default for all tests"""
        super(
            ClassificationPermissionsCollectionRemoveMultipleTestCase, self
        ).setUp()
        self.research_project = self.create_research_project(owner=self.alice)

        self.collection = self.create_research_project_collection(
            project=self.research_project,
            collection=self.create_collection(self.alice)
        )
        self.login_alice()

    def _call_helper(self, project):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        pdata which is json"""
        collection = self.create_classification_project_collection(
            project=project,
            collection=self.collection
        )
        params = {
            'pks': collection.pk
        }

        url = reverse(
            'media_classification:project_collection_delete_multiple'
        )
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_action_owner(self):
        """Project owner can delete collections from project"""
        project = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project,
        )
        self.assertTrue(self._call_helper(project))

    def test_action_role_admin(self):
        """User with `Admin` role can delete collections from project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        )
        self.assertTrue(self._call_helper(project))

    def test_action_role_expert(self):
        """User with `Expert` role cannot delete collections from project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        )
        self.assertFalse(self._call_helper(project))

    def test_action_role_collaborator(self):
        """
        User with `Collaborator` role cannot delete collections from project
        """
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
            roles=[(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        )
        self.assertFalse(self._call_helper(project))

    def test_action_no_roles(self):
        """User without any role cannot delete collections from project"""
        project = self.create_classification_project(
            owner=self.ziutek,
            research_project=self.research_project,
        )
        self.assertFalse(self._call_helper(project))


class ClassificationProjectTestCase(
    BaseClassificationProjectTestCase, CollectionTestMixin
):
    """Tests related to modifying data for classification project by performing
    various accions"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationProjectTestCase, self).setUp()
        self.research_project = self.create_research_project(owner=self.alice)
        self.login_alice()

    def test_dashboard_projects(self):
        """Logged in user in dashboard can see list of own projects.
        Other users projectsare exluded"""

        self.create_classification_project(
            owner=self.ziutek, research_project=self.research_project,
            enable_crowdsourcing=False
        )
        self.create_classification_project(
            owner=self.alice, research_project=self.research_project,
            enable_crowdsourcing=False
        )
        url = reverse('accounts:dashboard')
        response = self.assert_access_granted(url)
        projects = self.assert_context_variable(
            response, 'classification_projects'
        )
        self.assertEqual(projects.count(), 1)

    def test_create(self):
        """
        Using create view logged in user that has enough permissions can
        create new classification project.
        """
        collection = self.create_collection(owner=self.alice)

        research_project_collection = \
            self.create_research_project_collection(
                project=self.research_project,
                collection=collection
            )
        url = reverse('media_classification:project_create')

        name = 'Test classification project'
        params = {
            'name': name,
            'research_project': self.research_project.pk,
            'status': ClassificationProjectStatus.ONGOING,
            'classificator=': '',
            'enable_crowdsourcing': 'on',
            'enable_sequencing=on': 'on',
            'classification_project_collections-0-collection':
                research_project_collection.pk,
            'classification_project_collections-0-enable_crowdsourcing': 'on',
            'classification_project_collections-0-enable_sequencing_experts':
                'on',
            'classification_project_collections-0-id=': '',
            'classification_project_collections-0-is_active': 'on',
            'classification_project_collections-INITIAL_FORMS': 0,
            'classification_project_collections-MAX_NUM_FORMS': 1000,
            'classification_project_collections-TOTAL_FORMS': 1,
            'classification_project_roles-0-id=': '',
            'classification_project_roles-0-name':
                ClassificationProjectRoleLevels.EXPERT,
            'classification_project_roles-0-user': self.ziutek.pk,
            'classification_project_roles-INITIAL_FORMS': 0,
            'classification_project_roles-MAX_NUM_FORMS': 1000,
            'classification_project_roles-TOTAL_FORMS': 1,
        }

        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302, response.status_code)

        self.assertTrue(
            ClassificationProject.objects.filter(
                name=name,
            ).exists()
        )
        self.assertTrue(
            ClassificationProjectRole.objects.filter(
                user=self.ziutek,
                classification_project__name=name,
                name=ClassificationProjectRoleLevels.EXPERT
            ).exists()
        )

        self.assertTrue(
            ClassificationProjectCollection.objects.filter(
                project__name=name,
                collection=research_project_collection
            ).exists()
        )

    def test_update(self):
        """
        Using update view logged in user that has enough permissions can
        change existing classification project.
        """
        roles = [(self.ziutek, ClassificationProjectRoleLevels.EXPERT)]
        project = self.create_classification_project(
            owner=self.alice, research_project=self.research_project,
            roles=roles
        )

        research_collection = self.create_research_project_collection(
            project=self.research_project,
            collection=self.create_collection(owner=self.alice)
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=project,
                collection=research_collection
            )

        role = ClassificationProjectRole.objects.get(
            user=self.ziutek,
            classification_project=project,
            name=ClassificationProjectRoleLevels.EXPERT
        )

        name = 'Updated test project'
        params = {
            'name': name,
            'research_project': self.research_project.pk,
            'status': ClassificationProjectStatus.ONGOING,
            'classificator=': '',
            'enable_crowdsourcing': '',
            'enable_sequencing=on': '',
            'classification_project_collections-0-DELETE': 'on',
            'classification_project_collections-0-collection':
                research_collection.pk,
            'classification_project_collections-0-enable_crowdsourcing': 'on',
            'classification_project_collections-0-enable_sequencing_experts':
                'on',
            'classification_project_collections-0-id':
                classification_collection.pk,
            'classification_project_collections-0-is_active': 'on',
            'classification_project_collections-INITIAL_FORMS': 1,
            'classification_project_collections-MAX_NUM_FORMS': 1000,
            'classification_project_collections-TOTAL_FORMS': 1,
            'classification_project_roles-0-DELETE': 'on',
            'classification_project_roles-0-id': role.pk,
            'classification_project_roles-0-name':
                ClassificationProjectRoleLevels.EXPERT,
            'classification_project_roles-0-user': self.ziutek.pk,
            'classification_project_roles-INITIAL_FORMS': 1,
            'classification_project_roles-MAX_NUM_FORMS': 1000,
            'classification_project_roles-TOTAL_FORMS': 1,
        }

        url = self.get_classification_project_update_url(project=project)
        redirection = self.get_classification_project_details_url(
            project=project
        )
        self.assert_redirect(
            url, redirection=redirection, method='post', data=params
        )
        project = ClassificationProject.objects.get(pk=project.pk)

        # Name has been changed
        self.assertEqual(project.name, name)

        # Role has been deleted
        self.assertFalse(
            ClassificationProjectRole.objects.filter(pk=role.pk).exists()
        )

        # Collection has been deleted
        self.assertFalse(
            ClassificationProjectCollection.objects.filter(
                pk=classification_collection.pk
            ).exists()
        )

    def test_delete(self):
        """
        Using delete view logged in user that has enough permissions can
        delete existing project using GET.
        """

        roles = [(self.ziutek, ClassificationProjectRoleLevels.EXPERT)]
        project = self.create_classification_project(
            owner=self.alice, roles=roles,
            research_project=self.research_project
        )

        research_collection = self.create_research_project_collection(
            project=self.research_project,
            collection=self.create_collection(owner=self.alice)
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=project,
                collection=research_collection
            )

        url = self.get_classification_project_delete_url(project=project)

        self.client.get(url)
        self.assertFalse(
            ClassificationProject.objects.filter(pk=project.pk).exists()
        )

        # Role has been deleted
        self.assertFalse(
            ClassificationProjectRole.objects.filter(
                user=self.ziutek,
                classification_project=project,
                name=ClassificationProjectRoleLevels.EXPERT
            ).exists()
        )

        # Collection has been deleted
        self.assertFalse(
            ClassificationProjectCollection.objects.filter(
                pk=classification_collection.pk
            ).exists()
        )

    def test_delete_multiple(self):
        """
        Using delete view logged in user that has enough permissions can
        delete multiple projects using POST.
        """

        project1 = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project
        )
        project2 = self.create_classification_project(
            owner=self.alice,
            research_project=self.research_project
        )

        url = reverse('media_classification:project_delete_multiple')

        pks_list = [project1.pk, project2.pk, self.TEST_PK]

        response = self.client.post(
            url, data={'pks': ",".join(map(str, pks_list))}
        )

        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

        self.assert_invalid_pk(response)
        self.assertFalse(
            ClassificationProject.objects.filter(pk__in=pks_list).exists()
        )

    def test_add_collection(self):
        """
        Using add collection to classification project view logged in user
        that has enough permissions can add collection to classification
        project
        """
        project = self.create_classification_project(
            owner=self.alice, research_project=self.research_project
        )

        research_collection = self.create_research_project_collection(
            project=self.research_project,
            collection=self.create_collection(owner=self.alice)
        )

        url = reverse('media_classification:project_collection_add')

        data = {
            'classification_project': project.pk,
            'pks': ",".join([str(research_collection.pk), str(self.TEST_PK)])
        }
        response = self.assert_access_granted(url, method='post', data=data)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assertEqual(project.collections.count(), 1)
        self.assert_invalid_pk(response, field='added')

    def test_delete_collection(self):
        """
        Using remove collection from classification project view logged in
        user that has enough permissions can remove classification project
        collection from classification project
        """
        project = self.create_classification_project(
            owner=self.alice, research_project=self.research_project
        )
        research_collection = self.create_research_project_collection(
            project=self.research_project,
            collection=self.create_collection(owner=self.alice)
        )
        classification_collection = \
            self.create_classification_project_collection(
                project=project,
                collection=research_collection
            )

        url = reverse(
            'media_classification:project_collection_delete',
            kwargs={'pk': classification_collection.pk}
        )
        redirection = self.get_classification_project_list_url()
        self.assert_redirect(url, redirection=redirection)

        self.assertEqual(project.collections.count(), 0)

    def test_delete_multiple_collections(self):
        """
        Using remove collection from classification project view logged in
        user that has enough permissions can remove multiple classification
        project collections from classification project in single request
        """
        project = self.create_classification_project(
            owner=self.alice, research_project=self.research_project
        )

        collection1 = self.create_classification_project_collection(
            project=project,
            collection=self.create_research_project_collection(
                project=self.research_project,
                collection=self.create_collection(owner=self.alice)
            )
        )

        collection2 = self.create_classification_project_collection(
            project=project,
            collection=self.create_research_project_collection(
                project=self.research_project,
                collection=self.create_collection(owner=self.alice)
            )
        )

        url = reverse(
            'media_classification:project_collection_delete_multiple'
        )
        params = {
            'pks': ",".join([
                str(collection1.pk),
                str(collection2.pk),
                str(self.TEST_PK)
            ]),
        }
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assert_invalid_pk(response)
        self.assertEqual(project.collections.count(), 0)

    def test_remove_approved_project(self):
        """When classification project contain at least one classification
        that has been approved, then removing this project won't
        delete record form database, but instead record is marked
        as disabled"""
        project = self.create_classification_project(
            owner=self.alice, research_project=self.research_project
        )
        resource = self.create_resource(owner=self.alice)

        collection = self.create_classification_project_collection(
            project=project,
            collection=self.create_research_project_collection(
                project=self.research_project,
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

        url = self.get_classification_project_delete_url(project=project)

        self.client.get(url)
        self.assertTrue(
            ClassificationProject.objects.filter(pk=project.pk).exists()
        )

        project = ClassificationProject.objects.get(pk=project.pk)
        self.assertTrue(project.disabled_at)
        self.assertTrue(project.disabled_by)
