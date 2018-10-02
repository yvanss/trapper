# -*- coding: utf-8 -*-
"""
Views used to handle logic related to user classification management
in media classification application
"""
from __future__ import unicode_literals

from django.shortcuts import redirect, get_object_or_404
from django.views import generic
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.utils.timezone import now

from bulk_update.helper import bulk_update
from braces.views import UserPassesTestMixin, JSONResponseMixin

from trapper.apps.media_classification.models import (
    ClassificationProject, UserClassification, 
    ClassificationProjectCollection,
    ClassificationDynamicAttrs
)
from trapper.apps.geomap.models import Deployment
from trapper.apps.common.views import LoginRequiredMixin
from trapper.apps.common.tools import parse_pks

User = get_user_model()


class UserClassificationGridContextMixin(object):
    """Mixin used with views that use any classification listing for changing
    list behaviour.
    This mixin can be used to:

    * change classifiction url (i.e. add filtering)
    * if classification project is specified then add all:

        * deployments assigned to resources within project
        * collections assigned to this project
    """
    def get_user_classification_url(self, **kwargs):
        return reverse('media_classification:api-user-classification-list')

    def get_user_classification_context(self, **kwargs):
        project = kwargs.get('project', None)
        is_admin = project.is_project_admin(self.request.user)
        context = {
            'data_url': self.get_user_classification_url(**kwargs),
            'project': project,
            'model_name': 'user classifications',
            'hide_delete': not is_admin,
            'hide_detail': True,
            'is_admin': is_admin
        }

        if project:

            context['users'] = User.objects.filter(
                user_classifications__classification__project=project
            ).values_list(
                'pk', 'username'
            ).order_by('username').distinct()

            context['deployments'] = Deployment.objects.filter(
                resources__classifications__project=project
            ).values_list(
                'pk', 'deployment_id'
            ).order_by('deployment_id').distinct()

            context['collections'] = ClassificationProjectCollection.objects.filter(
                project=project
            ).values_list(
                'pk', 'collection__collection__name'
            ).order_by('collection__collection__name').distinct()

        return context


class UserClassificationListView(
    LoginRequiredMixin, UserPassesTestMixin, generic.ListView,
    UserClassificationGridContextMixin
):
    """List view of the
    :class:`apps.media_classification.models.UserClassification` instances.
    UserClassifications are always limited to project that contains them.

    This view is accesible only for persons that have enough permissions
    to view user classifications.
    """

    template_name = 'media_classification/user_classifications/list.html'
    raise_exception = True

    def get_user_classification_url(self, **kwargs):
        """Alter url for user classifications DRF API, to get only user classifications
        that belong to given classification project """
        project_pk = self.kwargs['pk']
        return '{url}?project={pk}'.format(
            url=reverse('media_classification:api-user-classification-list'),
            pk=project_pk
        )

    def get_project(self):
        """Return classification project for given pk or return HTTP 404"""
        return get_object_or_404(ClassificationProject, pk=self.kwargs['pk'])

    def test_func(self, user):
        """Check if user has enough permissions to view classifications"""
        return self.get_project().can_view_classifications(user)

    def get_context_data(self, **kwargs):
        """Update context used to render template with user classification context
        and filters"""

        project = self.get_project()
        context = {
            'user_classification_context': self.get_user_classification_context(
                project=project
            ),
        }
        context['user_classification_context']['update_redirect'] = False

        return context

    def get_queryset(self):
        pass


view_user_classification_list = UserClassificationListView.as_view()


class BulkApproveUserClassificationView(
        LoginRequiredMixin, UserPassesTestMixin,
        generic.View, JSONResponseMixin
):
    """
    """
    http_method_names = ['post']
    raise_exception = True

    def get_project(self):
        """Return classification project for given pk or return HTTP 404"""
        return get_object_or_404(ClassificationProject, pk=self.kwargs['pk'])

    def test_func(self, user):
        """Check if user has enough permissions to aprove user classifications"""
        self.project = self.get_project()
        return self.project.is_project_admin(user)

    def raise_exception_handler(self, request, *args, **kwargs):
        """When this method is defined and raise_exception is set to True,
        instead of throwing forbidden page - this method is called.
        By default it responses with json context with information that
        authentication is required"""
        context = {'status': False, 'msg': 'Authentication required'}
        return self.render_json_response(context)

    def post(self, request, *args, **kwargs):
        user = request.user
        timestamp = now()
        data = request.POST.get('pks', None)

        if data:
            values = parse_pks(pks=data)
            user_classifications = UserClassification.objects.filter(
                classification__project=self.project,
                pk__in=values
            ).select_related(
                'classification', 'owner'
            ).prefetch_related(
                'dynamic_attrs'
            )
            total = len(user_classifications)
            if not total:
                status = False
                msg = 'No items to delete (most probably you have no permission to do that).'
                context = {'status': status, 'msg': msg}
                return self.render_json_response(context)

            users = [k.owner for k in user_classifications]
            if len(set(users)) != 1:
                status = False
                msg = (
                    'You can run this action only for a set of classifications '
                    'that all belong to a one user.'
                )
                context = {'status': status, 'msg': msg}
                return self.render_json_response(context)


            # bulk update classification objects
            classifications_to_update = []
            dynamic_attrs_objects = []

            for uc in user_classifications:
                classification = uc.classification
                classification.status = True
                classification.approved_by_id = user.pk
                classification.approved_at = str(timestamp)
                classification.approved_source_id = uc.pk
                classification.static_attrs = uc.static_attrs
                classifications_to_update.append(classification)

                for dynamic_row in uc.dynamic_attrs.all():
                    dynamic_attrs_objects.append(
                        ClassificationDynamicAttrs(
                            classification_id=classification.pk,
                            attrs=dynamic_row.attrs
                        )
                    )

            bulk_update(classifications_to_update, update_fields=[
                'status', 'approved_by_id', 'approved_at',
                'approved_source_id', 'static_attrs'
            ])

            # bulk delete ClassificationDynamicAttrs objects
            ClassificationDynamicAttrs.objects.filter(
                classification__in=classifications_to_update
            ).delete()

            # bulk create ClassificationDynamicAttrs objects
            ClassificationDynamicAttrs.objects.bulk_create(dynamic_attrs_objects)

        else:
            status = False
            msg = 'Invalid request'

        status = True
        msg = (
            'You have successfully approved <strong>{n}</strong> user '
            'classifications.'.format(n=total)
        )
        context = {'status': status, 'msg': msg}
        return self.render_json_response(context)


view_user_classification_bulk_approve = BulkApproveUserClassificationView.as_view()
