# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, ResearchProjectTestMixin, SequenceTestMixin,
    ClassificationProjectTestMixin, CollectionTestMixin,
    ClassificationTestMixin, ClassificatorTestMixin
)

from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectRoleLevels, ClassificationStatus, ClassifyMessages
)


class BaseClassifyTestCase(
    ExtendedTestCase, SequenceTestMixin, ResearchProjectTestMixin,
    ClassificationProjectTestMixin, CollectionTestMixin,
    ClassificationTestMixin, ClassificatorTestMixin
):
    def setUp(self):
        super(BaseClassifyTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()


class AnonymousClassifyTestCase(BaseClassifyTestCase):
    """Classify process logic for anonymous users"""

    def test_details(self):
        """Anonymous user has to login before seeing classify form"""
        url = reverse(
            'media_classification:classify',
            kwargs={'pk': 1}
        )
        self.assert_forbidden(url)

    def test_create(self):
        """
        Anonymous user has to login before getting access to create
        classification action
        """
        url = reverse(
            'media_classification:classify',
            kwargs={'pk': 1}
        )
        self.assert_forbidden(url, method='post', data={})

    def test_update(self):
        """
        Anonymous user has to login before getting access to update
        classification action
        """
        url = reverse(
            'media_classification:classify',
            kwargs={'pk': 1}
        )
        self.assert_forbidden(url, method='post', data={})

    def test_approve(self):
        """
        Anonymous user has to login before getting access to approve
        classification action
        """
        url = reverse(
            'media_classification:classify',
            kwargs={'pk': 1}
        )
        self.assert_forbidden(
            url, method='post', data={'approve_classification': True}
        )

    def test_create_multiple(self):
        """
        Anonymous user has to login before getting access to create
        multiple classifications action
        """
        url = reverse(
            'media_classification:classify',
            kwargs={'pk': 1}
        )
        self.assert_forbidden(
            url, method='post', data={'classify_multiple': True}
        )

    def test_box_approve(self):
        """
        Anonymous user has to login before getting access to approve
        classification action in classification box
        """
        url = reverse(
            'media_classification:classify_approve',
            kwargs={'pk': 1}
        )
        self.assert_auth_required(url, method='post', data={})


class ClassifyFormPermissionsTestCase(BaseClassifyTestCase):
    """Classify access create/update form permission logic for authenticated
    users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassifyFormPermissionsTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
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
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        classification, user_classification = self.create_classification(
            owner=owner, resource=resource,
            collection=classification_collection,
            project=classification_project,
            status=ClassificationStatus.APPROVED
        )

        self.url = reverse(
            'media_classification:classify',
            kwargs={
                'pk': classification.pk
            }
        )

    def test_owner(self):
        """Owner can see classify form"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_role_admin(self):
        """User with ADMIN role can see classify form"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_role_expert(self):
        """User with EXPERT role can see classify form"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_role_collaborator(self):
        """User with COLLABORATOR role can see classify form"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url)

    def test_no_roles(self):
        """User with no roles cannot see classify form"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(self.url)


class ClassifyCreatePermissionsTestCase(BaseClassifyTestCase):
    """Classify create process logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassifyCreatePermissionsTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """Prepare all necessary objects to perform test for different
        project permissions"""
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
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        classification, user_classification = self.create_classification(
            owner=owner, resource=resource,
            collection=classification_collection,
            project=classification_project,
            status=ClassificationStatus.APPROVED
        )

        self.url = reverse(
            'media_classification:classify',
            kwargs={
                'pk': classification.pk,
            }
        )

    def test_owner(self):
        """Project owner can create classification"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url, method='post', data={})

    def test_role_admin(self):
        """User with ADMIN role can create classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url, method='post', data={})

    def test_role_expert(self):
        """User with EXPERT role can create classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url, method='post', data={})

    def test_role_collaborator(self):
        """User with COLLABORATOR role can create classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        self.assert_access_granted(self.url, method='post', data={})

    def test_no_roles(self):
        """User with no roles cannot create classification"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(self.url, method='post', data={})


class ClassifyUpdatePermissionsTestCase(BaseClassifyTestCase):
    """Classify update logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassifyUpdatePermissionsTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """Prepare all necessary objects to perform test for different
        project permissions"""
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

        classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project,
            classificator=classificator
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        classification, user_classification = self.create_classification(
            owner=owner, resource=resource,
            collection=classification_collection,
            project=classification_project,
            status=ClassificationStatus.REJECTED
        )

        self.url = reverse(
            'media_classification:classify_user',
            kwargs={
                'pk': classification.pk,
                'user_pk': owner.pk
            }
        )

    def test_owner(self):
        """Owner can update classification"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(self.url, method='post', data={})
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_role_admin(self):
        """User with ADMIN role can update other user classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(self.url, method='post', data={})
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_role_expert(self):
        """User with EXPERT role cannot update other user classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(self.url, method='post', data={})
        self.assert_has_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_role_collaborator(self):
        """
        User with COLLABORATOR role cannot update other user classification
        """
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(self.url, method='post', data={})
        self.assert_has_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_no_roles(self):
        """User with no roles cannot update other user classification"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(self.url, method='post', data={})


class ClassifyApprovePermissionsTestCase(BaseClassifyTestCase):
    """Classify approve process logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassifyApprovePermissionsTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """Prepare all necessary objects to perform test for different
        project permissions"""
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

        classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project,
            classificator=classificator
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        classification, user_classification = self.create_classification(
            owner=owner, resource=resource,
            collection=classification_collection,
            project=classification_project,
            status=ClassificationStatus.REJECTED
        )

        self.url = reverse(
            'media_classification:classify',
            kwargs={
                'pk': classification.pk
            }
        )

    def test_owner(self):
        """Project owner can approve other user classification"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={'approve_classification': True}
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_role_admin(self):
        """User with ADMIN role can approve other user classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={'approve_classification': True}
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_role_expert(self):
        """User with EXPERT role cannot approve other user classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={'approve_classification': True}
        )
        self.assert_has_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_role_collaborator(self):
        """
        User with COLLABORATOR role cannot approve other user classification
        """
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={'approve_classification': True}
        )
        self.assert_has_message(
            response, ClassifyMessages.MSG_PERMS_REQUIRED
        )

    def test_no_roles(self):
        """User with no roles cannot see classification details"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(
            self.url, method='post', data={'approve_classification': True}
        )


class ClassifyCreateMultiplePermissionsTestCase(BaseClassifyTestCase):
    """Classify multiple process permission logic for authenticated users"""

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassifyCreateMultiplePermissionsTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """Prepare all necessary objects to perform test for different
        project permissions"""
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

        classification_project = self.create_classification_project(
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        classification, user_classification = self.create_classification(
            owner=owner, resource=self.resource,
            collection=classification_collection,
            project=classification_project,
            status=ClassificationStatus.APPROVED
        )

        self.url = reverse(
            'media_classification:classify',
            kwargs={
                'pk': classification.pk
            }
        )

    def test_owner(self):
        """Project owner can create multiple classifications"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post',
            data={
                'classify_multiple': True,
                'selected_resources': self.resource.pk
            }
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_CLASSIFY_MULTIPLE_FAILED
        )

    def test_role_admin(self):
        """User with ADMIN role can create multiple classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post',
            data={
                'classify_multiple': True,
                'selected_resources': self.resource.pk
            }
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_CLASSIFY_MULTIPLE_FAILED
        )

    def test_role_expert(self):
        """User with EXPERT role can create multiple classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post',
            data={
                'classify_multiple': True,
                'selected_resources': self.resource.pk
            }
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_CLASSIFY_MULTIPLE_FAILED
        )

    def test_role_collaborator(self):
        """User with COLLABORATOR role can create multiple classifications"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post',
            data={
                'classify_multiple': True,
                'selected_resources': self.resource.pk
            }
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_CLASSIFY_MULTIPLE_FAILED
        )

    def test_no_roles(self):
        """User with no roles cannot create classification"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        self.assert_forbidden(
            self.url, method='post',
            data={
                'classify_multiple': True,
                'selected_resources': self.resource.pk
            }
        )


class ClassifyBoxApprovePermissionsTestCase(BaseClassifyTestCase):
    """
    """

    def setUp(self):
        """Login alice by default for all tests"""
        super(ClassifyBoxApprovePermissionsTestCase, self).setUp()
        self.login_alice()

    def _call_helper(self, owner, roles):
        """Prepare all necessary objects to perform test for different
        project permissions"""
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
            owner=owner, roles=roles, research_project=research_project
        )

        classification_collection = \
            self.create_classification_project_collection(
                project=classification_project,
                collection=research_collection
            )

        classification, user_classification = self.create_classification(
            owner=owner, resource=resource,
            collection=classification_collection,
            project=classification_project,
            status=ClassificationStatus.REJECTED
        )

        user_classification = self.create_user_classification(
            owner=owner, classification=classification
        )

        self.url = reverse(
            'media_classification:classify_approve',
            kwargs={
                'pk': user_classification.pk,
            }
        )

    def test_owner(self):
        """Project owner can approve own classifications"""
        owner = self.alice
        roles = None
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={}, follow=True
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_APPROVE_PERMS
        )

    def test_role_admin(self):
        """User with ADMIN role can approve other user classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.ADMIN)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={}, follow=True
        )
        self.assert_has_no_message(
            response, ClassifyMessages.MSG_APPROVE_PERMS
        )

    def test_role_expert(self):
        """User with EXPERT role cannot approve other user classification"""
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.EXPERT)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={}, follow=True
        )
        self.assert_has_message(
            response, ClassifyMessages.MSG_APPROVE_PERMS
        )

    def test_role_collaborator(self):
        """
        User with COLLABORATOR role cannot approve other user classification
        """
        owner = self.ziutek
        roles = [(self.alice, ClassificationProjectRoleLevels.COLLABORATOR)]
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={}, follow=True
        )
        self.assert_has_message(
            response, ClassifyMessages.MSG_APPROVE_PERMS
        )

    def test_no_roles(self):
        """User with no roles cannot approve other user classification"""
        owner = self.ziutek
        roles = None
        self._call_helper(owner=owner, roles=roles)
        response = self.assert_access_granted(
            self.url, method='post', data={}, follow=True
        )
        self.assert_has_message(
            response, ClassifyMessages.MSG_APPROVE_PERMS
        )
