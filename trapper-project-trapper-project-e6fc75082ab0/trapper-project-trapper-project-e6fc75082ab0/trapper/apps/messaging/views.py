# -*- coding: utf-8 -*-
"""Module that contains logic for working with messaging application"""
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.views import generic
from django.shortcuts import redirect
from django.contrib import messages

from braces.views import UserPassesTestMixin

from trapper.apps.messaging.models import (
    Message, CollectionRequest
)
from trapper.apps.messaging.forms import MessageForm
from trapper.apps.messaging.taxonomies import MessageType
from trapper.apps.common.views import HashedDetailView, LoginRequiredMixin


class MessageDetailView(
    LoginRequiredMixin, UserPassesTestMixin, HashedDetailView
):
    """
    View used to show details of given message.
    Before page with message is shown, message is tested if currently logged in
    user have proper rights
    """
    model = Message

    raise_exception = True

    def test_func(self, user):
        """Check if user have enough permissions to display messsage"""
        return self.get_object().can_detail(user=user)

    def get_object(self, *args, **kwargs):
        """Get message by given hashcode and mark it as received"""
        message = super(MessageDetailView, self).get_object(*args, **kwargs)
        message = message.mark_received(user=self.request.user)
        return message

view_message_detail = MessageDetailView.as_view()


class MessageCreateView(LoginRequiredMixin, generic.CreateView):
    """View used for creating new messages"""
    form_class = MessageForm
    template_name = 'messaging/message_create.html'

    def get_form_kwargs(self):
        """Update form `kwargs` so they contain current `request`"""
        kwargs = super(MessageCreateView, self).get_form_kwargs()
        # We need this to exclude current user from receipient list
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """If form is valid, then :class:`apps.messaging.models.Message`
        `user_from` attribute is updated with currently logged in user, and
        proper message is shown to user"""
        form.instance.user_from = self.request.user
        messages.add_message(
            self.request,
            messages.SUCCESS,
            'Message has been sent'
        )
        return super(MessageCreateView, self).form_valid(form)

    def form_invalid(self, form):
        """If form is invalid, then error messages should be shown to user"""
        messages.add_message(
            self.request,
            messages.ERROR,
            'Message form contains errors'
        )
        return super(MessageCreateView, self).form_invalid(form)


view_message_create = MessageCreateView.as_view()


class MessageListView(LoginRequiredMixin, generic.ListView):
    """Base class used for listing currently logged in user messages."""
    model = Message
    context_object_name = 'message_list'
    is_inbox = None
    paginate_by = 20

    def get_context_data(self, **kwargs):
        """Additional information are required to display inbox or outbox
        messages"""
        context = super(MessageListView, self).get_context_data(**kwargs)
        context['is_inbox'] = self.is_inbox
        return context

view_message_list = MessageListView.as_view()


class MessageInboxView(MessageListView):
    """View used to display messages that were sent to currently logged in
    user"""
    template_name = "messaging/message_inbox.html"
    is_inbox = True

    def get_queryset(self):
        """Return all messsages assigned to user"""
        return self.request.user.received_messages.exclude(
            message_type__in=[
                MessageType.COLLECTION_REQUEST,
                MessageType.RESOURCE_REQUEST
            ]
        ).select_related('user_from', 'user_from__userprofile')

view_message_inbox = MessageInboxView.as_view()


class MessageOutboxView(MessageListView):
    """View used to display messages that were sent by currently logged in
    user"""
    template_name = "messaging/message_outbox.html"
    is_inbox = False

    def get_queryset(self):
        """Return all messages that user sent"""
        return self.request.user.sent_messages.all()

view_message_outbox = MessageOutboxView.as_view()


class CollectionRequestListView(LoginRequiredMixin, generic.ListView):
    """View used to display collection requests that were sent to currently
    logged in user"""
    context_object_name = 'collection_requests'
    paginate_by = 20

    model = CollectionRequest
    template_name = 'messaging/collection_request_list.html'

    def get_queryset(self):
        """Return all collection access requests. If request was resolved
        then 'resolve' link will be unavailable"""
        return self.request.user.collection_requests.all().select_related(
            'project', 'message__user_from', 'message__user_from__userprofile'
        ).prefetch_related('collections')

view_collection_request_list = CollectionRequestListView.as_view()


class BaseResolveRequestView(
    LoginRequiredMixin, UserPassesTestMixin, generic.DetailView
):
    """
    Base class that holds logic responsible for resolving access requests
    """
    http_method_names = ['post']
    redirect_url = None

    raise_exception = True

    def test_func(self, user):
        """Resolving is allowed only for recipients of requests"""
        return self.get_object().user == user

    def post(self, request, *args, **kwargs):
        """Approve or reject access to resources or collections"""
        obj = self.get_object()

        is_approved = 'yes' in self.request.POST
        obj.resolve_access(user=request.user, is_approved=is_approved)
        return redirect(reverse(self.redirect_url))


class ResolveCollectionRequestView(BaseResolveRequestView):
    """View used to resolve access to collections requests"""
    model = CollectionRequest
    redirect_url = 'messaging:collection_request_list'

view_collection_request_resolve = ResolveCollectionRequestView.as_view()


class BaseRevokeRequestView(
    LoginRequiredMixin, UserPassesTestMixin, generic.DetailView
):
    """Base class used for revoking access for requests that were approved"""
    http_method_names = ['post']
    redirect_url = None

    raise_exception = True

    def test_func(self, user):
        """Resolving is allowed only for recipients of requests"""
        return self.get_object().user == user

    def post(self, request, *args, **kwargs):
        """Revoke access rights to resources or collections"""
        obj = self.get_object()
        is_revoked = 'yes' in self.request.POST

        if is_revoked:
            obj.resolve_revoke(user=request.user)
        return redirect(reverse(self.redirect_url))


class RevokeCollectionRequestView(BaseRevokeRequestView):
    """View used for revoking access to collections"""
    model = CollectionRequest
    redirect_url = 'messaging:collection_request_list'

view_collection_request_revoke = RevokeCollectionRequestView.as_view()
