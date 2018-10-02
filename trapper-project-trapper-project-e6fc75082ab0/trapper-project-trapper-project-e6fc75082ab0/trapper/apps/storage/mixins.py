# -*- coding: utf-8 -*-
"""
Module contains common logic for :class:`apps.storage.models.Resource` and
:class:`apps.storage.models.Collection` models.
"""

from django.core.urlresolvers import reverse

from trapper.middleware import get_current_user

__all__ = ['APIContextManagerMixin', 'AccessModelMixin']


class APIContextManagerMixin(object):
    """Mixin for ModelManger which provide methods for DRF API:

    * update data
    * detail data
    * delete data
    """

    def api_update_context(self, item, user):
        """
        Method used in DRF api to return update url if user has permissions
        """
        context = None
        if item.can_update(user):
            context = reverse(self.url_update, kwargs={'pk': item.pk})
        return context

    def api_detail_context(self, item, user):
        """
        Method used in DRF api to return detail url if user has permissions
        """
        context = None
        #if item.can_view(user):
        context = reverse(self.url_detail, kwargs={'pk': item.pk})
        return context

    def api_delete_context(self, item, user):
        """
        Method used in DRF api to return delete url if user has permissions
        """
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context


class AccessModelMixin(object):
    """Mixin used with :class:`storage.Resource` and
    :class:`storage.Collection` models to check basic permissions
    """

    def can_view(self, user=None, member_levels=None):
        """
        Checks if given user has access to details.

        :param user: if passed, permissions will be checked against given
            user will be used. If user is None then current request
            will be checked for currently logged in user and this user
            will be used. Otherwise only PUBLIC resources are available
            to view details
        :param member_levels: roles required to view details. By default
            ACCESS level is required to view details

        :return: boolean access status
        """
        user = user or get_current_user()

        member_levels = member_levels or [
            self.member_levels.ACCESS,
            self.member_levels.ACCESS_REQUEST,
        ]

        if self.status == self.status_choices.PUBLIC:
            return True
        else:
            user = user or get_current_user()
            access_status = (
                # Legacy code begin
                self.owner == user or user in self.managers.all()
                # Legacy code end
            )
            if user.is_authenticated():
                params = {
                    'user': user,
                    'level__in': member_levels,
                    self._meta.model_name: self
                }

                access_status = (
                    access_status or
                    self.members.through.objects.filter(**params).exists()
                )
        return access_status

    def can_delete(self, user=None, member_levels=None):
        """
        Check if given user has access to delete a record.

        :param user: if passed, permissions will be checked against given
            user will be used. If user is None then current request
            will be checked for currently logged in user and this user
            will be used. Otherwise access is forbidden

        :return: boolean access status
        """

        user = user or get_current_user()
        if not user.is_authenticated():
            return False
        result = (
            self.owner_id == user.pk or
            user in self.managers.all()
        )
        return result

    def can_update(self, user=None, member_levels=None):
        """
        Check if given user has access to update a record.

        :param user: if passed, permissions will be checked against given
            user will be used. If user is None then current request
            will be checked for currently logged in user and this user
            will be used. Otherwise access is forbidden

        :return: boolean access status
        """

        user = user or get_current_user()
        if not user.is_authenticated():
            return False
        result = (
            self.owner_id == user.pk or
            user in self.managers.all()
        )
        return result
