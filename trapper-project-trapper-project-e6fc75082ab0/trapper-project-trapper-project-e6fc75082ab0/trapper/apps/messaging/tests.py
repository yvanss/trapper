# -*- coding: utf-8 -*-

import itertools

from django.core.urlresolvers import reverse
from django.utils.lorem_ipsum import words, paragraph

from trapper.apps.common.utils.test_tools import (
    ExtendedTestCase, ResourceTestMixin, CollectionTestMixin,
    ResearchProjectTestMixin
)
from trapper.apps.messaging.models import (
    Message, CollectionRequest,
)
from trapper.apps.messaging.taxonomies import MessageType
from trapper.apps.storage.models import CollectionMember
from trapper.apps.storage.taxonomy import CollectionMemberLevels


class MessagingTestCase(ExtendedTestCase):
    """Tests related to messaging application access by registered and logged
    in user"""

    def setUp(self):
        super(MessagingTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()
        self.summon_eric()

    def create_messages(self):
        users = [self.alice, self.eric, self.ziutek]
        message_matrix = list(itertools.product(
            users, MessageType.DICT_CHOICES.keys()
        ))

        for user, message_type in message_matrix:
            Message.objects.create(
                subject=words(3),
                text=paragraph(),
                user_from=self.alice,
                user_to=user
            )

    def test_list_inbox(self):
        """Inbox show only current user standard messages"""
        url = reverse('messaging:message_inbox')
        self.create_messages()

        self.login_alice()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        messages_list = response.context[-1]['object_list']
        for message in messages_list:
            self.assertEqual(message.message_type, MessageType.STANDARD)
            self.assertEqual(message.user_to, self.alice)

    def test_list_outbox(self):
        url = reverse('messaging:message_outbox')
        self.create_messages()
        self.login_alice()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        message_list = response.context[-1]['object_list']
        for message in message_list:
            self.assertEqual(message.message_type, MessageType.STANDARD)
            self.assertEqual(message.user_from, self.alice)

    def test_create_message(self):
        """Send message to another active user"""

        url = reverse('messaging:message_create')
        self.login_alice()

        response = self.client.post(
            url,
            {
                'subject': words(4),
                'user_to': self.ziutek.pk,
                'text': paragraph()
            }
        )
        self.assertEqual(Message.objects.count(), 1)

        message = Message.objects.all()[0]

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.has_header('location'))
        self.assertTrue(
            response['location'].endswith(message.get_absolute_url())
        )

        self.assertEqual(message.user_from, self.alice)
        self.assertEqual(message.user_to, self.ziutek)
        self.assertEqual(message.message_type, MessageType.STANDARD)
        self.assertIsNone(message.date_received)

    def test_create_message_myself(self):
        """User cannot send message to himself"""
        url = reverse('messaging:message_create')
        self.login_alice()

        response = self.client.post(
            url,
            {
                'subject': words(4),
                'user_to': self.alice.pk,
                'text': paragraph()
            }
        )

        self.assertFalse(Message.objects.exists())
        self.assertEqual(response.status_code, 200)
        form = response.context[-1]['form']
        self.assertFalse(form.is_valid())
        self.assertIn('user_to', form.errors)

    def test_create_message_inactive(self):
        """User cannot send message to inactive user"""
        url = reverse('messaging:message_create')

        self.login_alice()

        response = self.client.post(
            url,
            {
                'subject': words(4),
                'user_to': self.eric.pk,
                'text': paragraph()
            }
        )

        self.assertFalse(Message.objects.exists())
        self.assertEqual(response.status_code, 200)
        form = response.context[-1]['form']
        self.assertFalse(form.is_valid())
        self.assertIn('user_to', form.errors)

    def test_dashboard_messages(self):
        """In dashboard user can see standard messages sent to him"""
        url = reverse('accounts:dashboard')
        self.login_alice()

        self.create_messages()

        response = self.client.get(url)

        message_list = response.context[-1]['inbox_messages']
        for message in message_list:
            self.assertEqual(message.message_type, MessageType.STANDARD)
            self.assertEqual(message.user_to, self.alice)

    def test_unauth_access_message_details(self):
        """User should not have access to other messsages"""
        self.login_alice()

        self.summon_john()
        message = Message.objects.create(
            subject=words(3),
            text=paragraph(),
            user_from=self.ziutek,
            user_to=self.john
        )
        url = message.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class AnonymousMessagingTestCase(ExtendedTestCase):
    """Tests related to messaging application access by anonymous users"""

    def test_access_inbox(self):
        """Anonymous users cannot access message inbox"""
        url = reverse('messaging:message_inbox')
        self.assert_auth_required(url=url)

    def test_access_outbox(self):
        """Anonymous users cannot access message outbox"""
        url = reverse('messaging:message_outbox')
        self.assert_auth_required(url=url)

    def test_access_create(self):
        """Anonymous users cannot access message create form"""
        url = reverse('messaging:message_create')
        self.assert_auth_required(url=url)

    def test_access_message_details(self):
        """User should not have access to other messsages"""
        self.summon_ziutek()
        self.summon_alice()

        message = Message.objects.create(
            subject=words(3),
            text=paragraph(),
            user_from=self.ziutek,
            user_to=self.alice
        )
        url = message.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class CollectionRequestTestCase(
    ExtendedTestCase, CollectionTestMixin, ResearchProjectTestMixin
):
    def setUp(self):
        super(CollectionRequestTestCase, self).setUp()
        self.summon_alice()
        self.summon_ziutek()

        self.resource = self.create_resource(owner=self.alice)
        self.resource2 = self.create_resource(owner=self.alice)

        self.collection = self.create_collection(
            owner=self.alice, resources=[self.resource, self.resource2]
        )
        self.research_project = self.create_research_project(owner=self.ziutek)

        self.message = Message.objects.create(
            subject=words(3),
            text=paragraph(),
            user_from=self.ziutek,
            user_to=self.alice,
            message_type=MessageType.COLLECTION_REQUEST
        )

        self.collection_request = CollectionRequest.objects.create(
            name='collection request',
            project=self.research_project,
            user=self.alice,
            user_from=self.ziutek,
            message=self.message
        )
        self.collection_request.collections.add(self.collection)

    def test_request_list(self):
        """Under collection request section currently logged in user should
        see only messages that are requests for access to collection"""
        url = reverse('messaging:collection_request_list')
        self.login_alice()

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        request_list = response.context[-1]['object_list']

        # Request list should not be empty
        self.assertTrue(request_list.count())
        for request in request_list:
            self.assertEqual(request.user, self.alice)
            self.assertEqual(
                request.message.message_type,
                MessageType.COLLECTION_REQUEST
            )

    def test_approve(self):
        """Test approve mechanics"""

        url = reverse(
            'messaging:collection_request_resolve',
            kwargs={'pk': self.collection_request.pk}
        )
        self.login_alice()

        self.assertEqual(CollectionMember.objects.count(), 0)

        response = self.client.post(url, {'yes': True})

        redirect_url = reverse('messaging:collection_request_list')

        # After approval user is redirected to request list
        self.assertRedirects(response, redirect_url, 302)

        collection_request = CollectionRequest.objects.get(
            pk=self.collection_request.pk
        )
        self.assertTrue(collection_request.is_approved)

        # and user that requested access is now member with ACCESS status
        # and have basic access to resources
        self.assertTrue(
            CollectionMember.objects.filter(
                collection=self.collection,
                user=self.ziutek,
                level=CollectionMemberLevels.ACCESS
            ).exists()
        )

    def test_reject(self):
        """Test reject mechanics"""
        url = reverse(
            'messaging:collection_request_resolve',
            kwargs={'pk': self.collection_request.pk}
        )
        self.login_alice()

        # Check that tere are no members
        self.assertEqual(CollectionMember.objects.count(), 0)

        response = self.client.post(url, {'no': True})

        redirect_url = reverse('messaging:collection_request_list')

        # After approval user is redirected to request list
        self.assertRedirects(response, redirect_url, 302)

        # collection request approval status is set to False
        self.assertFalse(self.collection_request.is_approved)

        self.assertEqual(CollectionMember.objects.count(), 0)

    def test_revoke(self):
        """Test revoke access mechanics"""

        self.collection_request.approve(user=self.ziutek)

        # ziutek is now member with ACCESS level
        self.assertTrue(
            CollectionMember.objects.filter(
                collection=self.collection,
                user=self.ziutek,
                level=CollectionMemberLevels.ACCESS
            ).exists()
        )

        url = reverse(
            'messaging:collection_request_revoke',
            kwargs={'pk': self.collection_request.pk}
        )
        self.login_alice()

        response = self.client.post(url, {'yes': True})

        redirect_url = reverse('messaging:collection_request_list')

        # After approval user is redirected to request list
        self.assertRedirects(response, redirect_url, 302)

        self.assertFalse(self.collection_request.is_approved)


class AnonymousCollectionRequestTestCase(ExtendedTestCase):
    def test_access_request_list(self):
        """Anonymous users cannot have collection requests"""
        url = reverse('messaging:collection_request_list')
        self.assert_auth_required(url=url)

    def test_access_approve_reject(self):
        """Anonymous users cannot approve or reject requests.
        Collection pk doesn't matter here.
        Approve or reject uses the same url and logic.
        """
        url = reverse(
            'messaging:collection_request_resolve',
            kwargs={'pk': 1}
        )
        self.assert_forbidden(url=url)

    def test_access_revoke(self):
        """Anonymous users cannot revoke granted access.
        Collection pk doesn't matter here.
        """
        url = reverse(
            'messaging:collection_request_revoke',
            kwargs={'pk': 1}
        )
        self.assert_forbidden(url=url)
