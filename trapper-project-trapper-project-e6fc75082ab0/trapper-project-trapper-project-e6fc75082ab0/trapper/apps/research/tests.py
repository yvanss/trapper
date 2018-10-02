# -*- coding: utf-8 -*-

import json

from django.core.urlresolvers import reverse
from django.conf import settings

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, CollectionTestMixin, ResearchProjectTestMixin,
    ResourceTestMixin, ClassificationProjectTestMixin
)
from trapper.apps.research.taxonomy import (
    ResearchProjectStatus, ResearchProjectRoleType,
)
from trapper.apps.research.models import ResearchProject, ResearchProjectRole


class BaseResearchProjectTestCase(ExtendedTestCase, ResearchProjectTestMixin):
    def setUp(self):
        super(BaseResearchProjectTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

    def get_research_project_details_url(self, project):
        return reverse('research:project_detail', kwargs={'pk': project.pk})

    def get_research_project_update_url(self, project):
        return reverse('research:project_update', kwargs={'pk': project.pk})

    def get_research_project_delete_url(self, project):
        return reverse('research:project_delete', kwargs={'pk': project.pk})

    def get_research_project_list_url(self):
        return reverse('research:project_list')


class AnonymousResearchTestCase(BaseResearchProjectTestCase):
    """Research project logic for anonymous users"""

    def test_research_project_list(self):
        """Anonymous user can access to research projects list"""
        url = reverse('research:project_list')
        self.assert_access_granted(url)

    def test_research_project_json(self):
        """Anonymous user can see all accepted projects"""

        url = reverse('research:api-research-project-list')

        project_accepted = self.create_research_project(owner=self.alice)
        project_rejected = self.create_research_project(
            owner=self.alice, status=ResearchProjectStatus.REJECTED
        )

        response = self.client.get(url)
        content = json.loads(response.content)['results']

        project_pk_list = [item['pk'] for item in content]

        self.assertIn(
            project_accepted.pk, project_pk_list, 'Accepted not shown'
        )
        self.assertNotIn(
            project_rejected.pk, project_pk_list, 'Rejected shown'
        )

    def test_project_details(self):
        """
        Anonymous user has no permissions to access rejected project details.
        """

        project_accepted = self.create_research_project(owner=self.alice)
        project_rejected = self.create_research_project(
            owner=self.alice, status=ResearchProjectStatus.REJECTED
        )

        url_approved = reverse(
            'research:project_detail', kwargs={'pk': project_accepted.pk}
        )
        url_rejected = reverse(
            'research:project_detail', kwargs={'pk': project_rejected.pk}
        )
        self.assert_access_granted(url=url_approved)
        self.assert_forbidden(url=url_rejected)

    def test_project_create(self):
        """Anonymous user has to login before creating project"""
        url = reverse('research:project_create')
        self.assert_auth_required(url=url)

    def test_project_delete(self):
        """Anonymous user has to login before delete project"""
        url = reverse('research:project_delete', kwargs={'pk': 1})
        self.assert_auth_required_json(url=url, method='get')
        self.assert_auth_required_json(url=url, method='post')

    def test_project_delete_multiple(self):
        """Anonymous user has to login before delete multiple projects
        Delete is handled by Ajax"""
        url = reverse('research:project_delete_multiple')
        self.assert_auth_required_json(url=url, method='post')

    def test_project_update(self):
        """Anonymous user has no permissions to update project"""
        url = reverse('research:project_update', kwargs={'pk': 1})
        self.assert_forbidden(url=url, method='post')

    def test_add_collection_to_project(self):
        """Anonymous user has no permissions to add storage collection to
        research project."""
        url = reverse('research:project_collection_add')
        self.assert_forbidden(url=url, method='post')

    def test_remove_collection_from_project(self):
        """
        Anonymous user has no permissions to remove collection from project
        """
        url = reverse('research:project_collection_delete', kwargs={'pk': 1})
        self.assert_auth_required_json(url=url, method='post')

    def test_remove_multiple_collections_from_project(self):
        """
        Anonymous user has no permissions to remove multiple collections
        from project
        """
        url = reverse('research:project_collection_delete_multiple')
        self.assert_auth_required_json(url=url, method='post')


class ResearchPermissionsListTestCase(BaseResearchProjectTestCase):
    """Research project list permission logic for authenticated users"""

    def test_research_project_list(self):
        """Authenticated user can access to research projects list"""

        self.login_alice()
        url = reverse('research:project_list')
        self.assert_access_granted(url)

    def test_research_project_json(self):
        """Authenticated user can see all accepted projects"""

        self.login_alice()
        url = reverse('research:api-research-project-list')

        project_accepted = self.create_research_project(owner=self.alice)
        project_rejected = self.create_research_project(
            owner=self.alice, status=ResearchProjectStatus.REJECTED
        )

        response = self.client.get(url)
        content = json.loads(response.content)['results']

        project_pk_list = [item['pk'] for item in content]

        self.assertIn(
            project_accepted.pk, project_pk_list, 'Accepted not shown'
        )
        self.assertNotIn(
            project_rejected.pk, project_pk_list, 'Rejected shown'
        )


class ResearchPermissionsDetailsTestCase(
    BaseResearchProjectTestCase, CollectionTestMixin, ResourceTestMixin,
    ClassificationProjectTestMixin
):
    """Details permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ResearchPermissionsDetailsTestCase, self).setUp()
        self.login_alice()

    def test_details_owner(self):
        """Project owner can access details"""
        project = self.create_research_project(owner=self.alice)
        url = self.get_research_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_role_admin(self):
        """User with `Admin` role can access details"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.ADMIN)]
        )
        url = self.get_research_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_role_expert(self):
        """User with `Expert` role can access details"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.EXPERT)]
        )
        url = self.get_research_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_role_collaborator(self):
        """User with `Collaborator` role can access details"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.COLLABORATOR)]
        )
        url = self.get_research_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_details_no_roles(self):
        """User without any role can access details (see different content)"""
        project = self.create_research_project(owner=self.ziutek)
        url = self.get_research_project_details_url(project=project)
        self.assert_access_granted(url)

    def test_list_collections_allowed(self):
        """If user has enough permissions to view project details,
        he can see collections assigned to particular project through api"""
        self.login_alice()

        project = self.create_research_project(owner=self.alice)

        self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.alice)
        )

        url = u'{url}?project={pk}'.format(
            url=reverse('research:api-research-project-collection-list'),
            pk=project.pk
        )
        response = self.assert_access_granted(url)
        self.assertEqual(len(json.loads(response.content)['results']), 1)

    def test_list_collections_forbidden(self):
        """If user has not enough permissions to view project details,
        he cannot see collections assigned to particular project through api"""
        self.login_alice()

        project = self.create_research_project(owner=self.ziutek)

        self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.ziutek)
        )

        url = u'{url}?project={pk}'.format(
            url=reverse('research:api-research-project-collection-list'),
            pk=project.pk
        )
        response = self.assert_access_granted(url)
        self.assertEqual(len(json.loads(response.content)['results']), 0)

    def test_list_classification_projects_allowed(self):
        """If user has enough permissions to view project details,
        he can see classification projects that research project is assigned
        to through api"""
        self.login_alice()

        research_project = self.create_research_project(owner=self.alice)

        self.create_classification_project(
            owner=self.alice,
            research_project=research_project,
        )

        url = '{url}?research_project={pk}'.format(
            url=reverse(
                'media_classification:api-classification-project-list'
            ),
            pk=research_project.pk
        )
        response = self.assert_access_granted(url)
        self.assertEqual(len(json.loads(response.content)['results']), 1)

    def test_list_classification_projects_forbidden(self):
        """If user has not enough permissions to view project details,
        he can see only classification projects with crowdsourcing enabled
        that research project is assigned to through api"""
        self.login_alice()

        research_project = self.create_research_project(owner=self.ziutek)

        self.create_classification_project(
            owner=self.ziutek,
            research_project=research_project,
            enable_crowdsourcing=True
        )
        self.create_classification_project(
            owner=self.ziutek,
            research_project=research_project,
            enable_crowdsourcing=False
        )

        url = '{url}?research_project={pk}'.format(
            url=reverse(
                'media_classification:api-classification-project-list'
            ),
            pk=research_project.pk
        )
        response = self.assert_access_granted(url)

        self.assertEqual(len(json.loads(response.content)['results']), 1)


class ResearchPermissionsUpdateTestCase(BaseResearchProjectTestCase):
    """Update permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests and prepare default params"""
        super(ResearchPermissionsUpdateTestCase, self).setUp()
        self.login_alice()
        self.params = {
            'name': 'test-project',
            'acronym': 'test',
            'project_roles-TOTAL_FORMS': 0,
            'project_roles-INITIAL_FORMS': 0,
            'project_roles-MAX_NUM_FORMS': 1000
        }

    def test_update_owner(self):
        """Project owner can update project"""
        project = self.create_research_project(owner=self.alice)
        url = self.get_research_project_update_url(project=project)
        redirection = self.get_research_project_details_url(project=project)
        self.assert_redirect(url, redirection, method='post', data=self.params)

    def test_update_role_admin(self):
        """User with `Admin` role can update project"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.ADMIN)]
        )
        url = self.get_research_project_update_url(project=project)
        redirection = self.get_research_project_details_url(project=project)
        self.assert_redirect(url, redirection, method='post', data=self.params)

    def test_update_role_expert(self):
        """User with `Expert` role cannot update project"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.EXPERT)]
        )
        url = self.get_research_project_update_url(project=project)

        self.assert_forbidden(url, method='post', data=self.params)

    def test_update_role_collaborator(self):
        """User with `Collaborator` role cannot update project"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.COLLABORATOR)]
        )
        url = self.get_research_project_update_url(project=project)
        self.assert_forbidden(url, method='post', data=self.params)

    def test_update_no_roles(self):
        """User without any role cannot update project"""
        project = self.create_research_project(owner=self.ziutek)
        url = self.get_research_project_update_url(project=project)
        self.assert_forbidden(url, method='post', data=self.params)


class ResearchPermissionsDeleteTestCase(BaseResearchProjectTestCase):
    """
    Delete permission logic for logged in user

    .. note::
        Delete multiple uses the same permission logic
    """

    def setUp(self):
        """Login alice by default for all tests"""
        super(ResearchPermissionsDeleteTestCase, self).setUp()
        self.login_alice()

    def test_delete_owner(self):
        """Project owner can delete project"""
        project = self.create_research_project(owner=self.alice)
        url = self.get_research_project_delete_url(project=project)
        redirection = self.get_research_project_list_url()
        self.assert_redirect(url, redirection)

    def test_update_role_admin(self):
        """User with `Admin` role can access details"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.ADMIN)]
        )
        url = self.get_research_project_delete_url(project=project)
        redirection = self.get_research_project_list_url()
        self.assert_redirect(url, redirection)

    def test_update_role_expert(self):
        """User with `Expert` role can access details"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.EXPERT)]
        )
        url = self.get_research_project_delete_url(project=project)

        self.assert_forbidden(url)

    def test_update_role_collaborator(self):
        """User with `Collaborator` role can access details"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.COLLABORATOR)]
        )
        url = self.get_research_project_delete_url(project=project)
        self.assert_forbidden(url)

    def test_update_no_roles(self):
        """User without any role can access details (see different content)"""
        project = self.create_research_project(owner=self.ziutek)
        url = self.get_research_project_delete_url(project=project)
        self.assert_forbidden(url)


class ResearchPermissionsAddCollectionTestCase(
    BaseResearchProjectTestCase, CollectionTestMixin
):
    """Add collection permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests and prepare default params"""
        super(ResearchPermissionsAddCollectionTestCase, self).setUp()
        self.login_alice()

        collection1 = self.create_collection(owner=self.alice)
        collection2 = self.create_collection(owner=self.alice)

        self.params = {
            'pks': ",".join([str(collection1.pk), str(collection2.pk)]),
        }

    def _call_helper(self, project):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        url = reverse('research:project_collection_add')

        self.params['research_project'] = project.pk
        response = self.assert_access_granted(
            url, method='post', data=self.params
        )

        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_add_collection_owner(self):
        """Project owner can add collections"""
        project = self.create_research_project(owner=self.alice)

        status = self._call_helper(project=project)
        self.assertTrue(status)

    def test_add_collection_role_admin(self):
        """User with `Admin` role can add collection"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.ADMIN)]
        )
        status = self._call_helper(project=project)
        self.assertTrue(status)

    def test_add_collection_role_expert(self):
        """User with `Expert` role cannot add collection"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.EXPERT)]
        )
        status = self._call_helper(project=project)
        self.assertFalse(status)

    def test_add_collection_role_collaborator(self):
        """User with `Collaborator` role cannot add collection"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.COLLABORATOR)]
        )
        status = self._call_helper(project=project)
        self.assertFalse(status)

    def test_add_collection_no_roles(self):
        """User without any role cannot add collection"""
        project = self.create_research_project(owner=self.ziutek)
        status = self._call_helper(project=project)
        self.assertFalse(status)


class ResearchPermissionsDeleteCollectionTestCase(
    BaseResearchProjectTestCase, CollectionTestMixin
):
    """Delete collection permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(
            ResearchPermissionsDeleteCollectionTestCase, self
        ).setUp()
        self.login_alice()

    def _get_url(self, project):
        """All tests use the same logic so most of it is defined here"""

        project_collection = self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.alice)
        )

        url = reverse(
            'research:project_collection_delete',
            kwargs={'pk': project_collection.pk}
        )
        return url

    def test_delete_collection_owner(self):
        """Project owner can delete collection"""
        project = self.create_research_project(owner=self.alice)
        url = self._get_url(project=project)
        redirection = self.get_research_project_details_url(project=project)
        self.assert_redirect(url, redirection=redirection)

    def test_delte_collection_role_admin(self):
        """User with `Admin` role can delete collection"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.ADMIN)]
        )
        url = self._get_url(project=project)
        redirection = self.get_research_project_details_url(project=project)
        self.assert_redirect(url, redirection=redirection)

    def test_delete_collection_role_expert(self):
        """User with `Expert` role cannot delete collection"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.EXPERT)]
        )
        url = self._get_url(project=project)
        self.assert_forbidden(url)

    def test_delete_collection_role_collaborator(self):
        """User with `Collaborator` role cannot delete collection"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.COLLABORATOR)]
        )
        url = self._get_url(project=project)
        self.assert_forbidden(url)

    def test_delete_collection_no_roles(self):
        """User without any role cannot delete collection"""
        project = self.create_research_project(owner=self.ziutek)
        url = self._get_url(project=project)
        self.assert_forbidden(url)


class ResearchPermissionsDeleteMultipleCollectionTestCase(
    BaseResearchProjectTestCase, CollectionTestMixin
):
    """Delete collection permission logic for logged in user"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(
            ResearchPermissionsDeleteMultipleCollectionTestCase, self
        ).setUp()
        self.login_alice()

    def _call_helper(self, project):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        url = reverse('research:project_collection_delete_multiple')

        project_collection1 = self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.alice)
        )
        project_collection2 = self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.alice)
        )

        self.params = {
            'pks': ",".join(
                [str(project_collection1.pk), str(project_collection2.pk)]
            ),
        }
        response = self.assert_access_granted(
            url, method='post', data=self.params
        )

        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_delete_collection_owner(self):
        """Project owner can delete collections"""
        project = self.create_research_project(owner=self.alice)

        status = self._call_helper(project=project)
        self.assertTrue(status)

    def test_delte_collection_role_admin(self):
        """User with `Admin` role can delete collections"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.ADMIN)]
        )
        status = self._call_helper(project=project)
        self.assertTrue(status)

    def test_delete_collection_role_expert(self):
        """User with `Expert` role cannot delete collections"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.EXPERT)]
        )
        status = self._call_helper(project=project)
        self.assertFalse(status)

    def test_delete_collection_role_collaborator(self):
        """User with `Collaborator` role cannot delete collections"""
        project = self.create_research_project(
            owner=self.ziutek,
            roles=[(self.alice, ResearchProjectRoleType.COLLABORATOR)]
        )
        status = self._call_helper(project=project)
        self.assertFalse(status)

    def test_delete_collection_no_roles(self):
        """User without any role cannot delete collections"""
        project = self.create_research_project(owner=self.ziutek)
        status = self._call_helper(project=project)
        self.assertFalse(status)


class ResearchProjectTestCase(
    BaseResearchProjectTestCase, CollectionTestMixin
):
    """Tests related to modifying data for research project by performing
    various accions"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ResearchProjectTestCase, self).setUp()
        self.login_alice()

    def test_dashboard_projects(self):
        """Logged in user in dashboard can see list of own projects.
        Other users projectsare exluded"""

        self.create_research_project(owner=self.ziutek)
        self.create_research_project(owner=self.alice)
        url = reverse('accounts:dashboard')
        response = self.assert_access_granted(url)
        projects = self.assert_context_variable(response, 'research_projects')
        self.assertEqual(projects.count(), 1)

    def test_create(self):
        """
        Using create view logged in user that has enough permissions can
        create new research project.

        When new project is created it cannot be used, but admins get email
        notification

        Thist test verifies creating project roles aswell
        """

        url = reverse('research:project_create')

        name = 'Test research project'
        params = {
            'abstract': 'test abstract',
            'acronym': 'test',
            'description': 'test description',
            'methods': 'test methods',
            'name': name,
            'project_roles-0-name': ResearchProjectRoleType.EXPERT,
            'project_roles-0-user': self.ziutek.pk,
            'project_roles-INITIAL_FORMS': 0,
            'project_roles-MAX_NUM_FORMS': 1000,
            'project_roles-TOTAL_FORMS': 1,
        }

        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302, response.status_code)

        self.assertTrue(
            ResearchProject.objects.filter(
                name=name,
                status=ResearchProjectStatus.NOT_PROCESSED,
            ).exists()
        )
        self.assertTrue(
            ResearchProjectRole.objects.filter(
                user=self.ziutek,
                project=ResearchProject.objects.get(name=name),
                name=ResearchProjectRoleType.EXPERT
            ).exists()
        )

        # Test emails are sent to admins
        # self.assertEqual(len(self.mail.outbox), 1)
        # admin_emails = self.mail.outbox[0].to
        # for name, email in settings.ADMINS:
        #     self.assertIn(
        #         email,
        #         admin_emails,
        #         u"{name} is not in email receivers".format(name=name)
        #     )

    def test_update(self):
        """
        Using update view logged in user that has enough permissions can
        change existing collection.
        """
        roles = [(self.ziutek, ResearchProjectRoleType.EXPERT)]
        project = self.create_research_project(owner=self.alice, roles=roles)

        role = ResearchProjectRole.objects.get(
            user=self.ziutek,
            project=project,
            name=ResearchProjectRoleType.EXPERT
        )

        name = 'Updated test research project'
        params = {
            'abstract': 'test abstract',
            'acronym': 'test',
            'description': 'test description',
            'methods': 'test methods',
            'name': name,
            'project_roles-0-id': role.pk,
            'project_roles-0-name': ResearchProjectRoleType.EXPERT,
            'project_roles-0-user': self.ziutek.pk,
            'project_roles-0-DELETE': 'on',
            'project_roles-INITIAL_FORMS': 1,
            'project_roles-MAX_NUM_FORMS': 1000,
            'project_roles-TOTAL_FORMS': 1,
            }

        url = self.get_research_project_update_url(project=project)
        redirection = self.get_research_project_details_url(project=project)
        self.assert_redirect(
            url, redirection=redirection, method='post', data=params
        )
        project = ResearchProject.objects.get(pk=project.pk)

        # Name has been changed
        self.assertEqual(project.name, name)

        # Role has been deleted
        self.assertFalse(
            ResearchProjectRole.objects.filter(
                user=self.ziutek,
                project=project,
                name=ResearchProjectRoleType.EXPERT
            ).exists()
        )

    def test_delete(self):
        """
        Using delete view logged in user that has enough permissions can
        delete existing project using GET.
        """

        roles = [(self.ziutek, ResearchProjectRoleType.EXPERT)]
        project = self.create_research_project(owner=self.alice, roles=roles)

        url = self.get_research_project_delete_url(project=project)

        self.client.get(url)
        self.assertFalse(
            ResearchProject.objects.filter(pk=project.pk).exists()
        )

        self.assertFalse(
            ResearchProjectRole.objects.filter(
                user=self.ziutek,
                project=project,
                name=ResearchProjectRoleType.EXPERT
            ).exists()
        )

    def test_delete_multiple(self):
        """
        Using delete view logged in user that has enough permissions can
        delete multiple projects using POST.
        """

        project1 = self.create_research_project(owner=self.alice)
        project2 = self.create_research_project(owner=self.alice)

        url = reverse('research:project_delete_multiple')

        pks_list = [project1.pk, project2.pk, self.TEST_PK]

        response = self.client.post(
            url, data={'pks': ",".join(map(str, pks_list))}
        )
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assert_invalid_pk(response)
        self.assertFalse(
            ResearchProject.objects.filter(pk__in=pks_list).exists()
        )

    def test_add_collection(self):
        """
        Using add collection to research project view logged in user that has
        enough permissions can add collection to research project
        """
        project = self.create_research_project(owner=self.alice)
        collection = self.create_collection(owner=self.alice)

        url = reverse('research:project_collection_add')

        data = {
            'research_project': project.pk,
            'pks': ",".join([str(collection.pk), str(self.TEST_PK)])
        }
        response = self.assert_access_granted(url, method='post', data=data)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assert_invalid_pk(response, field='added')
        self.assertEqual(project.collections.count(), 1)

    def test_delete_collection(self):
        """
        Using remove collection from research project view logged in user that
        has enough permissions can remove research project collection from
        research project
        """
        project = self.create_research_project(owner=self.alice)
        collection = self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.alice)
        )
        url = reverse(
            'research:project_collection_delete', kwargs={'pk': collection.pk}
        )
        redirection = self.get_research_project_details_url(project=project)
        self.assert_redirect(url, redirection=redirection)

        self.assertEqual(project.collections.count(), 0)

    def test_delete_multiple_collections(self):
        """
        Using remove collection from research project view logged in user that
        has enough permissions can remove multiple research project collections
        from research project in single request
        """
        project = self.create_research_project(owner=self.alice)
        collection1 = self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.alice)
        )
        collection2 = self.create_research_project_collection(
            project=project,
            collection=self.create_collection(owner=self.alice)
        )
        url = reverse('research:project_collection_delete_multiple')
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
