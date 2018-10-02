# -*- coding: utf-8 -*-

import json

from django.core.urlresolvers import reverse

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, ResearchProjectTestMixin, SequenceTestMixin,
    ClassificationProjectTestMixin, CollectionTestMixin,
    ClassificationTestMixin
)

from trapper.apps.media_classification.models import Classification

from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectRoleLevels, ClassificationStatus
)


class BaseClassificationTestCase(
    ExtendedTestCase, SequenceTestMixin, ResearchProjectTestMixin,
    ClassificationProjectTestMixin, CollectionTestMixin,
    ClassificationTestMixin
):
    def setUp(self):
        super(BaseClassificationTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

    def get_classification_list_url(self, project):
        return reverse(
            'media_classification:classification_list',
            kwargs={'pk': project.pk}
        )

    def get_classification_detail_url(self, classification):
        return reverse(
            'media_classification:classification_detail',
            kwargs={'pk': classification.pk}
        )

    def get_classification_delete_url(self, classification):
        return reverse(
            'media_classification:classification_delete',
            kwargs={'pk': classification.pk}
        )


class AnonymousClassificationTestCase(BaseClassificationTestCase):
    """Classifications logic for anonymous users"""

    def test_classification_json(self):
        """Anonymous user cannot see classification API data"""
        url = reverse('media_classification:api-classification-list')
        self.assert_forbidden(url)

    def test_user_classification_json(self):
        """Anonymous user cannot see user classification API data"""
        url = reverse('media_classification:api-user-classification-list')
        self.assert_forbidden(url)

    def test_details(self):
        """Anonymous user has to login before seeing classification"""
        url = reverse(
            'media_classification:classification_detail', kwargs={'pk': 1}
        )
        self.assert_forbidden(url=url)

    def test_delete(self):
        """Anonymous user has to login before delete classification"""
        url = reverse(
            'media_classification:classification_delete', kwargs={'pk': 1}
        )
        self.assert_auth_required_json(url=url)

    def test_tags(self):
        """Anonymous user has to login before adding tags to classifications"""
        url = reverse(
            'media_classification:classification_tag', kwargs={'pk': 1}
        )
        self.assert_auth_required(url=url)


class ClassificationListPermissionTestCase(BaseClassificationTestCase):

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationListPermissionTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        resource = self.create_resource(owner=self.alice)
        collection = self.create_collection(
            owner=owner, resources=[resource]
        )

        research_project = self.create_research_project(
            owner=owner
        )

        research_collection = self.create_research_project_collection(
            project=research_project,
            collection=collection
        )

        self.classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=self.classification_project,
                collection=research_collection
            )

        self.classification, self.user_classification = self.create_classification(
            resource=resource,
            collection=classification_collection,
            project=self.classification_project,
            status = ClassificationStatus.APPROVED,
            owner=owner
        )

        url = reverse(
            'media_classification:api-classification-list'
        )

        response = self.assert_access_granted(url)
        content = json.loads(response.content)['results']

        pk_list = [item['pk'] for item in content]
        return pk_list

    def test_classification_owner_json(self):
        """Owner can see classifications in project"""
        owner = self.alice
        roles = None
        pk_list = self._call_helper(owner=owner, roles=roles)
        self.assertIn(self.classification.pk, pk_list)

    def test_classification_role_admin_json(self):
        """User with ADMIN role can see classifications in project"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        pk_list = self._call_helper(owner=owner, roles=roles)
        self.assertIn(self.classification.pk, pk_list)

    def test_classification_role_expert_json(self):
        """User with EXPERT role cannot see classifications in project"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        pk_list = self._call_helper(owner=owner, roles=roles)
        self.assertNotIn(self.classification.pk, pk_list)

    def test_classification_role_collaborator_json(self):
        """User with COLLABORATOR role can see classifications in project"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        pk_list = self._call_helper(owner=owner, roles=roles)
        self.assertIn(self.classification.pk, pk_list)

    def test_classification_no_roles_json(self):
        """User with no roles cannot see classifications in project"""
        owner = self.ziutek
        roles = None
        pk_list = self._call_helper(owner=owner, roles=roles)
        self.assertNotIn(self.classification.pk, pk_list)


class ClassificationDetailsPermissionTestCase(BaseClassificationTestCase):

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationDetailsPermissionTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        resource = self.create_resource(owner=self.alice)
        collection = self.create_collection(
            owner=owner, resources=[resource]
        )

        research_project = self.create_research_project(
            owner=owner
        )

        research_collection = self.create_research_project_collection(
            project=research_project,
            collection=collection
        )

        self.classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=self.classification_project,
                collection=research_collection
            )

        self.classification, self.user_classification = self.create_classification(
            resource=resource,
            collection=classification_collection,
            project=self.classification_project,
            status = ClassificationStatus.APPROVED,
            owner=owner
        )

        self.url = self.get_classification_detail_url(
            classification=self.user_classification
        )

    def test_owner(self):
        """Owner can see classification details"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_role_admin(self):
        """User with ADMIN role can see classification details"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_role_expert(self):
        """User with EXPERT role can see classification details"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_role_collaborator(self):
        """User with COLLABORATOR role can see classification details"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_no_roles(self):
        """User with no roles cannot see classification details"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(self.url)


class ClassificationDeletePermissionTestCase(BaseClassificationTestCase):

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationDeletePermissionTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        resource = self.create_resource(owner=self.alice)
        collection = self.create_collection(
            owner=owner, resources=[resource]
        )

        research_project = self.create_research_project(
            owner=owner
        )

        research_collection = self.create_research_project_collection(
            project=research_project,
            collection=collection
        )

        self.classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=self.classification_project,
                collection=research_collection
            )

        self.classification, self.user_classification = self.create_classification(
            resource=resource,
            collection=classification_collection,
            project=self.classification_project,
            status = ClassificationStatus.APPROVED,
            owner=owner
        )

        self.url = self.get_classification_delete_url(
            classification=self.classification
        )
        self.redirect_url = reverse(
            'media_classification:classification_list',
            kwargs={'pk': self.classification_project.pk}
        )

    def test_owner(self):
        """Owner can delete classification"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_redirect(self.url, self.redirect_url)

    def test_role_admin(self):
        """User with ADMIN role can delete classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_redirect(self.url, self.redirect_url)

    def test_role_expert(self):
        """User with EXPERT role cannot delete classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(self.url)

    def test_role_collaborator(self):
        """User with COLLABORATOR role cannot delete classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(self.url)

    def test_no_roles(self):
        """User with no roles cannot delete classification"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(self.url)


class ClassificationTagsPermissionTestCase(BaseClassificationTestCase):

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationTagsPermissionTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles, status):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        self.resource = self.create_resource(owner=self.alice)
        collection = self.create_collection(
            owner=owner, resources=[self.resource]
        )

        research_project = self.create_research_project(
            owner=owner
        )

        research_collection = self.create_research_project_collection(
            project=research_project,
            collection=collection
        )

        self.classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=self.classification_project,
                collection=research_collection
            )

        self.classification, self.user_classification = self.create_classification(
            resource=self.resource,
            collection=classification_collection,
            project=self.classification_project,
            status = status, owner=owner
        )

        params = {
            'Item1': 'on',
            'classifications': self.classification.pk
        }
        url = reverse(
            'media_classification:classification_tag',
            kwargs={'pk': self.classification_project.pk}
        )
        self.response = self.assert_access_granted(
            url, method='post', data=params
        )
        status = self.assert_json_context_variable(self.response, 'status')
        return status

    def test_owner(self):
        """Owner cannot create tags for selected unapproved classifications"""
        owner = self.alice
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.REJECTED
        )
        self.assertFalse(status)

    def test_role_admin(self):
        """User with ADMIN role cannot create tags for selected unapproved
        classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.REJECTED
        )
        self.assertFalse(status)

    def test_role_expert(self):
        """User with EXPERT role cannot create tags for selected unapproved
        classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.REJECTED
        )
        self.assertFalse(status)

    def test_role_collaborator(self):
        """User with COLLABORATOR role cannot create tags for selected
        unapproved classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.REJECTED
        )
        self.assertFalse(status)

    def test_no_roles(self):
        """User with no roles cannot create tags for selected unapproved
        classification"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.REJECTED
        )
        self.assertFalse(status)

    def test_owner_approved(self):
        """Owner can create tags for selected approved classifications"""
        owner = self.alice
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.APPROVED
        )
        self.assertTrue(status)

    def test_role_admin_approved(self):
        """User with ADMIN role can create tags for selected approved
        classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.APPROVED
        )
        self.assertTrue(status)

    def test_role_expert_approved(self):
        """User with EXPERT role can create tags for selected approved
        classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.APPROVED
        )
        self.assertTrue(status)

    def test_role_collaborator_approved(self):
        """User with COLLABORATOR role can create tags for selected
        approved classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.APPROVED
        )
        self.assertTrue(status)

    def test_no_roles_approved(self):
        """User with no roles cannot create tags for selected approved
        classification"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, status=ClassificationStatus.APPROVED
        )
        self.assertFalse(status)


class ClassificationTestCase(BaseClassificationTestCase):

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassificationTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles, status):
        """All tests call the same logic annd logged in user
        will get always response status 200. Difference is in response
        data which is json"""
        self.resource = self.create_resource(owner=self.alice)
        self.collection = self.create_collection(
            owner=owner, resources=[self.resource]
        )

        self.research_project = self.create_research_project(
            owner=owner
        )

        self.research_collection = self.create_research_project_collection(
            project=self.research_project,
            collection=self.collection
        )

        self.classification_project = self.create_classification_project(
            owner=owner, roles=roles,
            research_project=self.research_project
        )

        self.classification_collection = \
            self.create_classification_project_collection(
                project=self.classification_project,
                collection=self.research_collection
            )

        self.classification, self.user_classification = self.create_classification(
            resource=self.resource,
            collection=self.classification_collection,
            project=self.classification_project,
            status = status, owner=owner
        )

        self.user_classification = self.create_user_classification(
            owner=owner, classification=self.classification
        )

    def test_details(self):
        """Using classification details view user with enough permissions can
        see details of classification **in readonly** mode

        This test validate only basic components of detail view.
        """
        self._call_helper(
            owner=self.alice, roles=None, status=ClassificationStatus.APPROVED
        )

        url = self.get_classification_detail_url(self.user_classification)
        response = self.assert_access_granted(url)

        self.assertEqual(
            self.assert_context_variable(response, 'project'),
            self.classification_project
        )
        self.assertEqual(
            self.assert_context_variable(response, 'collection'),
            self.classification_collection
        )
        self.assertEqual(
            self.assert_context_variable(response, 'storage_collection'),
            self.collection
        )
        self.assertEqual(
            self.assert_context_variable(response, 'resource'),
            self.resource
        )

        self.assertTrue(
            self.assert_context_variable(response, 'is_readonly')
        )

    def test_delete(self):
        """Using classification delete view user that has enough permissions
        can delete classification. Not approved classfication is removed
        from database"""
        self._call_helper(
            owner=self.alice, roles=None, status=ClassificationStatus.REJECTED
        )
        url = self.get_classification_delete_url(self.classification)

        redirection_url = self.get_classification_list_url(
            project=self.classification.project
        )
        self.assert_redirect(url, redirection=redirection_url)
        self.assertFalse(
            Classification.objects.filter(pk=self.classification.pk)
        )

    def test_delete_approved(self):
        """Using classification delete view user that has enough permissions
        can delete classification. Approved classification is not removed
        from database but marked as disabled"""
        self._call_helper(
            owner=self.alice, roles=None, status=ClassificationStatus.APPROVED
        )
        url = self.get_classification_delete_url(self.classification)

        redirection_url = self.get_classification_list_url(
            project=self.classification.project
        )
        self.assert_redirect(url, redirection=redirection_url)
        self.assertTrue(
            Classification.objects.filter(pk=self.classification.pk)
        )

        classification = Classification.objects.get(pk=self.classification.pk)

        self.assertTrue(classification.disabled_at)
        self.assertEqual(classification.disabled_by, self.alice)

    def test_tag(self):
        """Using classification delete view user that has enough permissions
        can create tags for resources within classification."""
        self._call_helper(
            owner=self.alice, roles=None, status=ClassificationStatus.APPROVED
        )
        self.classification.static_attrs = {
            'Item1': 'Val1', 'Item2': 'Val2'
        }
        self.classification.save()
        url = reverse(
            'media_classification:classification_tag',
            kwargs={'pk': self.classification_project.pk}
        )

        tag_name = 'Item1'

        params = {
            tag_name: 'on',
            'classifications': self.classification.pk
        }
        self.assert_access_granted(url, method='post', data=params)

        self.assertTrue(
            self.resource.tags.filter(
                name=self.classification.static_attrs[tag_name]
            ).exists()
        )
