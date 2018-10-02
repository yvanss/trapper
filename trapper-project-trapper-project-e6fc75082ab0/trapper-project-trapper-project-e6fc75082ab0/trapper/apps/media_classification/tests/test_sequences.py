# -*- coding: utf-8 -*-

import json

from django.core.urlresolvers import reverse
from django.utils.timezone import now

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, ResearchProjectTestMixin, SequenceTestMixin,
    ClassificationProjectTestMixin, CollectionTestMixin
)

from trapper.apps.media_classification.models import (
    Sequence, SequenceResourceM2M, Classification
)

from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectRoleLevels, ClassificationStatus
)


class BaseSequenceTestCase(
    ExtendedTestCase, SequenceTestMixin, ResearchProjectTestMixin,
    ClassificationProjectTestMixin, CollectionTestMixin
):
    def setUp(self):
        super(BaseSequenceTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

    def get_sequence_update_url(self):
        return reverse('media_classification:sequence_update',)

    def get_sequence_delete_url(self):
        return reverse('media_classification:sequence_delete')

    def get_sequence_clone_url(self):
        return reverse('media_classification:sequence_clone')


class AnonymousSequenceTestCase(BaseSequenceTestCase):
    """Sequence logic for anonymous users"""

    def test_sequence_json(self):
        """Anonymous user cannot see API data"""
        url = reverse('media_classification:api-sequence-list')
        self.assert_forbidden(url)

    def test_create(self):
        """Anonymous user has to login before creating sequence"""
        url = reverse('media_classification:sequence_create')
        self.assert_auth_required_json(url=url)

    def test_update(self):
        """Anonymous user has no permissions to update project"""
        url = reverse('media_classification:sequence_update',)
        self.assert_auth_required_json(url=url, method='post')

    def test_delete(self):
        """Anonymous user has to login before delete project"""
        url = reverse('media_classification:sequence_delete')
        self.assert_auth_required_json(url=url, method='get')


class SequenceListPermissionsTestCase(BaseSequenceTestCase):
    """Sequence list permission logic for authenticated users"""

    def test_sequence_json(self):
        """Authenticated user can see all sequences"""

        self.login_alice()
        research_project = self.create_research_project(owner=self.alice)

        project = self.create_classification_project(
            owner=self.alice, research_project=research_project,
        )

        research_collection = self.create_research_project_collection(
            project=research_project,
            collection=self.create_collection(owner=self.alice)
        )

        classification_collection1 = \
            self.create_classification_project_collection(
                project=project,
                collection=research_collection
            )

        classification_collection2 = \
            self.create_classification_project_collection(
                project=project,
                collection=research_collection
            )

        seq1 = self.create_sequence(
            owner=self.ziutek, collection=classification_collection1
        )
        seq2 = self.create_sequence(
            owner=self.alice, collection=classification_collection2
        )
        url = reverse('media_classification:api-sequence-list')

        response = self.client.get(url)
        content = json.loads(response.content)

        pk_list = [item['pk'] for item in content]
        self.assertIn(seq1.pk, pk_list, 'Other not shown')
        self.assertIn(seq2.pk, pk_list, 'Own not shown')


class SequenceChangePermissionsTestCase(BaseSequenceTestCase):
    """Sequence create permission logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(SequenceChangePermissionsTestCase, self).setUp()
        self.sequence_id = '1'
        self.login_alice()

    def _call_helper(self, owner, roles, sequencing, is_approved):
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

        classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project,
            enable_sequencing=sequencing
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        if is_approved:
            Classification.objects.create(
                resource=resource,
                project=classification_project,
                collection=classification_collection,
                created_at=now(),
                status=ClassificationStatus.APPROVED,
                approved_by=self.alice,
                approved_at=now()
            )

        params = {
            'collection_pk': classification_collection.pk,
            'sequence_id': self.sequence_id,
            'description': 'new sequence',
            'project_pk': classification_project.pk,
            'resources': resource.pk,
        }
        url = reverse('media_classification:sequence_change')
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        return status

    def create_sequencing_owner(self):
        """Owner can create/change sequence on project that has sequencing
        enabled and no approved classifications"""
        owner = self.alice
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=False
        )
        self.assertTrue(status)

    def test_create_sequencing_admin(self):
        """User with ADMIN role can create/change sequence on project that has
        sequencing enabled and no approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=False
        )
        self.assertTrue(status)

    def test_create_sequencing_expert(self):
        """User with EXPERT role can create/change sequence on project that has
        sequencing enabled and no approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=False
        )
        self.assertTrue(status)

    def test_create_sequencing_collaborator(self):
        """User with COLLABORATOR role can create/change sequence on project
        that has sequencing enabled and no approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=False
        )
        self.assertTrue(status)

    def test_create_sequencing_no_roles(self):
        """User with no roles cannot create/change sequence on project that has
        sequencing enabled and no approved classifications"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=False
        )
        self.assertFalse(status)

    def test_create_no_sequencing_owner(self):
        """Owner can create/change sequence on project that has sequencing
        disabled and no approved classifications"""
        owner = self.alice
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=False
        )
        self.assertTrue(status)

    def test_create_no_sequencing_admin(self):
        """User with ADMIN role can create/change sequence on project that has
        sequencing disabled and no approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=False
        )
        self.assertTrue(status)

    def test_create_no_sequencing_expert(self):
        """User with EXPERT role cannot create/change sequence on project
        that has sequencing disabled and no approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=False
        )
        self.assertFalse(status)

    def test_create_no_sequencing_collaborator(self):
        """User with COLLABORATOR role cannot create/change sequence on
        project that has sequencing disabled and no approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=False
        )
        self.assertFalse(status)

    def test_create_no_sequencing_no_roles(self):
        """User with no roles cannot create/change sequence on project that has
        sequencing disabled and no approved classifications"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=False
        )
        self.assertFalse(status)

    def test_create_sequencing_approved_owner(self):
        """Owner can create/change sequence on project that has sequencing
        enabled and approved classifications"""
        owner = self.alice
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=True
        )
        self.assertTrue(status)

    def test_create_sequencing_approved_admin(self):
        """User with ADMIN role can create/change sequence on project that has
        sequencing enabled and approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=True
        )
        self.assertTrue(status)

    def test_create_sequencing_approved_expert(self):
        """User with EXPERT role cannot create/change sequence on project
        that has sequencing enabled and approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=True
        )
        self.assertFalse(status)

    def test_create_sequencing_approved_collaborator(self):
        """User with COLLABORATOR role cannot create/change sequence on
        project that has sequencing enabled and approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=True
        )
        self.assertFalse(status)

    def test_create_sequencing_approved_no_roles(self):
        """User with no roles cannot create/change sequence on project that has
        sequencing enabled and approved classifications"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=True, is_approved=True
        )
        self.assertFalse(status)

    def test_create_no_sequencing_approved_owner(self):
        """Owner can create/change sequence on project that has sequencing
        disabled and approved classifications"""
        owner = self.alice
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=True
        )
        self.assertTrue(status)

    def test_create_no_sequencing_approved_admin(self):
        """User with ADMIN role can create/change sequence on project that has
        sequencing disabled and approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=True
        )
        self.assertTrue(status)

    def test_create_no_sequencing_approved_expert(self):
        """User with EXPERT role cannot create/change sequence on project
        that has sequencing disabled and approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=True
        )
        self.assertFalse(status)

    def test_create_no_sequencing_approved_collaborator(self):
        """User with COLLABORATOR role cannot create/change sequence on project
        that has sequencing disabled and approved classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=True
        )
        self.assertFalse(status)

    def test_create_no_sequencing_approved_no_roles(self):
        """User with no roles cannot create/change sequence on project that has
        sequencing disabled and approved classifications"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(
            owner=owner, roles=roles, sequencing=False, is_approved=True
        )
        self.assertFalse(status)


class SequenceDeletePermissionsTestCase(BaseSequenceTestCase):
    """Sequence delete permission logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(SequenceDeletePermissionsTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, sequencing, roles):
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

        classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project,
            enable_sequencing=sequencing
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        self.sequence = self.create_sequence(
            owner=owner,
            collection=classification_collection,
        )
        SequenceResourceM2M.objects.create(
            sequence=self.sequence,
            resource=resource
        )

        self.url = reverse('media_classification:sequence_delete')
        self.params = {'pks': self.sequence.pk}
        response = self.assert_access_granted(
            self.url, method='post', data=self.params
        )
        status = self.assert_json_context_variable(response, 'status')
        return status

    def test_delete_sequencing_owner(self):
        """Owner can delete sequence on project that has sequencing enabled"""
        owner = self.alice
        roles = None
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertTrue(status)

    def test_delete_sequencing_role_admin(self):
        """User with ADMIN role can delete sequence on project that has
        sequencing enabled"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)

    def test_delete_sequencing_role_expert(self):
        """User with EXPERT role cannot delete sequence on project
        that has sequencing enabled"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)

    def test_delete_sequencing_role_collaborator(self):
        """User with COLLABORATOR role cannot delete sequence on project
        that has sequencing enabled"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)

    def test_delete_sequencing_no_roles(self):
        """User with no roles cannot delete sequence on project that has
        sequencing enabled"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)

    def test_delete_no_sequencing_owner(self):
        """
        Owner can delete sequence on project that has sequencing disaabled
        """
        owner = self.alice
        roles = None
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertTrue(status)

    def test_delete_no_sequencing_role_admin(self):
        """User with ADMIN role can delete sequence on project that has
        sequencing disabled"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)

    def test_delete_no_sequencing_role_expert(self):
        """User with EXPERT role cannot delete sequence on project
        that has sequencing disabled"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)

    def test_delete_no_sequencing_role_collaborator(self):
        """User with COLLABORATOR role cannot delete sequence on project
        that has sequencing disabled"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)

    def test_delete_no_sequencing_no_roles(self):
        """User with no roles cannot delete sequence on project that has
        sequencing disabled"""
        owner = self.ziutek
        roles = None
        status = self._call_helper(owner=owner, roles=roles, sequencing=True)
        self.assertFalse(status)


class SequenceTestCase(BaseSequenceTestCase):
    """Sequence logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(SequenceTestCase, self).setUp()
        self.login_alice()

        owner = self.alice
        self.sequence_id = '1'

        self.resource = self.create_resource(owner=owner)
        self.resource2 = self.create_resource(owner=owner)

        collection = self.create_collection(
            owner=owner, resources=[self.resource, self.resource2]
        )

        research_project = self.create_research_project(
            owner=owner
        )

        research_collection = self.create_research_project_collection(
            project=research_project,
            collection=collection
        )

        self.classification_project = self.create_classification_project(
            owner=owner, research_project=research_project,
            enable_sequencing=True
        )

        self.classification_collection = \
            self.create_classification_project_collection(
                project=self.classification_project,
                collection=research_collection
            )

    def test_create_sequence(self):
        """Using sequence create view user that has enough permissions can
        create sequence that will subgroup of classification
        project collection resources"""
        params = {
            'collection_pk': self.classification_collection.pk,
            'sequence_id': self.sequence_id,
            'description': 'new sequence',
            'project_pk': self.classification_project.pk,
            'resources': self.resource.pk,
        }
        url = reverse('media_classification:sequence_create')
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assertTrue(
            Sequence.objects.filter(
                sequence_id=params['sequence_id'],
                collection=self.classification_collection,
            ).exists()
        )
        sequence = Sequence.objects.get(sequence_id=params['sequence_id'])
        self.assertIn(self.resource, sequence.resources.all())

    def test_change_sequence(self):
        """Using sequence change view user that has enough permissions can
        alter sequence to modify resources that are in sequence"""
        sequence = self.create_sequence(
            owner=self.alice,
            collection=self.classification_collection,
        )
        SequenceResourceM2M.objects.create(
            sequence=sequence,
            resource=self.resource
        )
        params = {
            'collection_pk': self.classification_collection.pk,
            'sequence_id': sequence.sequence_id,
            'pk': sequence.pk,
            'description': 'updated new sequence',
            'project_pk': self.classification_project.pk,
            'resources': ",".join(
                [str(self.resource.pk), str(self.resource2.pk)]
            ),
        }

        url = reverse('media_classification:sequence_change')
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)

        sequence = Sequence.objects.get(pk=sequence.pk)
        resources = sequence.resources.all()

        self.assertIn(self.resource, resources)
        self.assertIn(self.resource2, resources)

    def test_delete_sequence(self):
        """Using sequence delete view user that has enough permissions can
        delete sequence"""
        sequence = self.create_sequence(
            owner=self.alice,
            collection=self.classification_collection,
        )
        SequenceResourceM2M.objects.create(
            sequence=sequence,
            resource=self.resource
        )

        params = {'pks': ",".join([str(sequence.pk), str(self.TEST_PK)])}

        url = reverse('media_classification:sequence_delete')
        response = self.assert_access_granted(url, method='post', data=params)
        status = self.assert_json_context_variable(response, 'status')
        self.assertTrue(status)
        self.assert_invalid_pk(response)
        self.assertFalse(
            Sequence.objects.filter(pk=sequence.pk).exists()
        )
