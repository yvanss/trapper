# -*- coding: utf-8 -*-
"""Module that contains logic related to creating or replying comments"""
from __future__ import unicode_literals

from django.views import generic
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseRedirect

from braces.views import UserPassesTestMixin

from trapper.apps.comments.forms import UserCommentForm
from trapper.apps.comments.models import UserComment
from trapper.apps.common.views import LoginRequiredMixin


class CommentCreateView(generic.CreateView):
    """Logic responsible for creating
    :class:`apps.comments.models.UserComment` instances

    By default all logged in users can create comments
    """

    model = UserComment
    form_class = UserCommentForm

    def get_success_url(self):
        """After successfull comment creation user is redirected to
        the same page user was on, or if this is not possible, then
        redirect to page defined in `settings.COMMENTS_REDIRECT_URL`
        """
        default_redirect = settings.COMMENTS_REDIRECT_URL
        return self.request.META.get('HTTP_REFERER', default_redirect)

    def form_valid(self, form):
        """If form is valid then show success message"""
        messages.add_message(
            self.request,
            messages.SUCCESS,
            'Your comment has been added'
        )
        return super(CommentCreateView, self).form_valid(form)

    def form_invalid(self, form):
        """If form is not valid then show error message"""
        messages.add_message(
            self.request,
            messages.ERROR,
            'Error creating new comment'
        )
        return HttpResponseRedirect(self.get_success_url())

view_comment_create = CommentCreateView.as_view()


class CommentDeleteView(
    LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView
):
    """Logic responsible for removing
    :class:`apps.comments.models.UserComment` instances

    By default comments cannot be removed
    """
    model = UserComment

    def test_func(self, user):
        """
        By default comments cannot be removed, but this can be changed if
        model that is comment is connected to has method `can_remove_comment`.

        This method (if defined) is used to test remove access status

        :param user: :class:`auth.User` instance that is used for testing

        :return: Boolean value with remove access status
        """
        result = False
        comment = self.get_object()
        content_object = comment.content_object

        handler = getattr(content_object, 'can_remove_comment', None)
        if callable(handler):
            result = handler(user=self.request.user)
        return bool(result)

    def get_success_url(self):
        """After successfull removal return to the place where request
        came from"""
        default_redirect = settings.COMMENTS_REDIRECT_URL
        return self.request.META.get('HTTP_REFERER', default_redirect)

    def get(self, request, *args, **kwargs):
        """Deletion should be available as well for GET requests.
        No confirmation is needed"""
        return self.delete(request, *args, **kwargs)

view_comment_delete = CommentDeleteView.as_view()
