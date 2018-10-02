# -*- coding: utf-8 -*-
"""
Views used to handle logic related to resource management in storage
application
"""
from __future__ import unicode_literals

import json

from django.db.models import Q
from django.conf import settings
from django.views import generic
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.auth import get_user_model
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.defaultfilters import filesizeformat

from braces.views import UserPassesTestMixin, JSONResponseMixin

from trapper.apps.common.views import (
    LoginRequiredMixin, BaseListFilterDataView
)
from trapper.apps.common.tools import parse_pks
from trapper.apps.common.views import (
    BaseDeleteView, BaseUpdateView, BaseBulkUpdateView
)
from trapper.apps.storage.models import Resource, Collection, ResourceUserRate
from trapper.apps.storage.forms import (
    ResourceForm, SimpleResourceForm, BulkUpdateResourceForm,
    ResourceDataPackageForm
)
from trapper.apps.accounts.models import UserProfile, UserTask
from trapper.apps.storage.taxonomy import ResourceType, ResourceStatus
from trapper.apps.storage.tasks import celery_create_media_package
from trapper.apps.research.models import ResearchProject
from trapper.apps.geomap.models import MapManagerUtils, Deployment
from trapper.apps.media_classification.models import ClassificationProject
from trapper.apps.sendfile.views import BaseServeFileView

User = get_user_model()


class ResourceGridContextMixin(object):
    """Mixin used with views that use any collection listing
    for changing list behaviour.
    This mixin can be used to:

    * change resource url (i.e. add filtering)
    * append collection url
    * research projects related to collection
    * collections used in filters
    * maps used in filters
    * tags used in filters
    """
    def get_resource_url(self, **kwargs):
        """Return standard DRF API url for resources"""
        return reverse('storage:api-resource-list')

    def get_resource_context(self, **kwargs):
        """Build resource context"""
        context = {
            'data_url': self.get_resource_url(**kwargs),
            'collections': Collection.objects.get_accessible().values_list(
                'pk', 'name'
            ),
            'deployments': Deployment.objects.get_accessible().values_list(
                'pk', 'deployment_id'
            ).order_by('deployment_id'),
            'tags': Resource.tags.values_list('pk', 'name'),
            'maps': MapManagerUtils.get_accessible(user=self.request.user),
            'model_name': "resources",
            'update_redirect': False,
        }
        return context


class ResourceListView(
        LoginRequiredMixin, generic.TemplateView, ResourceGridContextMixin
):
    """View used for rendering template with resource grid.
    Context of view is updated with :class:`ResourceGridContextMixin`
    """
    model = Resource
    template_name = 'storage/resources/resource_list.html'

    def get_context_data(self, **kwargs):
        """All we need to render base grid is:
        * Model name as title
        * Filter form instance

        This view is not serving any data. Data is read using DRF API
        """
        context = {
            'resource_context': self.get_resource_context(),
        }
        return context


view_resource_list = ResourceListView.as_view()


class ResourceListFilterDataView(BaseListFilterDataView):
    """View contain all values that should be used in resources filters

    .. warning::
        This view is not currently used.

        Filter values (selectes) are provided by :class:`ResourceListView`
    """

    def get_collections(self):
        """Get list of collections accessible to user"""
        collections = Collection.objects.get_accessible(
            user=self.request.user
        ).values_list(
            'name', flat=True
        )
        return zip(collections, collections)

    def get_filters_data(self):
        """Build filter values context"""
        return {
            'type': ResourceType.get_filter_choices(),
            'status': ResourceStatus.get_filter_choices(),
            'collections': self.get_collections(),
            'my_resources': self.request.user.is_authenticated()
        }


view_resource_list_filter_data = ResourceListFilterDataView.as_view()


class ResourceDetailView(
        LoginRequiredMixin, UserPassesTestMixin, generic.DetailView
):
    """View used for rendering details of specified resource.

    Before details are rendered, permissions are checked and if currently
    logged in user has not enough permissions to view details,
    proper message is displayed.
    """
    template_name = 'storage/resources/resource_detail.html'
    model = Resource
    raise_exception = True

    def test_func(self, user):
        """
        Resource details can be seen only if user has enough permissions
        """
        return self.get_object().can_view(user)

    def get_context_data(self, **kwargs):
        """Update context used to render template with data related to
        resources
        """
        user = self.request.user
        context = super(ResourceDetailView, self).get_context_data(**kwargs)
        resource = context['object']
        context['collections'] = resource.collection_set.get_accessible(
            user=user
        ).select_related('owner').prefetch_related('managers')
        context['research_projects'] = ResearchProject.objects.get_accessible(
            user=user
        ).filter(
            collections__resources=resource
        ).distinct()
        context['classification_projects'] = ClassificationProject.objects.get_accessible(
            user=user).filter(
                classification_project_collections__collection__collection__resources=resource
            ).distinct()
        context['my_rating'] = ResourceUserRate.objects.get_or_create(
            user=user, resource=resource
        )[0].rating
        context['average_rate'] = resource.rating.average or 0

        return context


view_resource_detail = ResourceDetailView.as_view()


class ResourceCreateView(LoginRequiredMixin, generic.CreateView):
    """Resource create view.
    It handles the creation of the :class:`apps.storage.models.Resource` objects.
    """

    template_name = 'storage/resources/resource_change.html'
    model = Resource
    form_class = ResourceForm

    def form_valid(self, form):
        """If form is valid then set `owner` as currently logged in user,
        and add message that resource has been created"""
        user = self.request.user
        form.instance.owner = user
        messages.add_message(
            self.request,
            messages.SUCCESS,
            'New resoure <strong>{name}</strong> has been added'.format(
                name=form.instance.name
            )
        )
        self.object = form.save()
        self.object.tags.clear()
        for tag in form.cleaned_data['tags']:
            self.object.tags.add(tag)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        """If form is not valid, form is re-rendered with error details,
        and message about unsuccessfull operation is shown"""
        messages.add_message(
            self.request,
            messages.ERROR,
            'Error creating new resource'
        )
        return super(ResourceCreateView, self).form_invalid(form)


view_resource_create = ResourceCreateView.as_view()


class ResourceDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    resources.

    Only resources that user has enough permissions for can be deleted
    """

    model = Resource
    redirect_url = 'storage:resource_list'


view_resource_delete = ResourceDeleteView.as_view()


class ResourceDefinePrefixView(
    LoginRequiredMixin, generic.View, JSONResponseMixin
):
    """View used to define resource name prefix for multiple resources
    in single request using AJAX

    Only resources owned by currently logged in user can be updated
    """
    raise_exception = True

    def raise_exception_handler(self, request, *args, **kwargs):
        """For ajax requests if user is not authenticated, instead of
        redirection or access denied page, json with proper message is
        created"""
        context = {'status': False, 'msg': 'Authentication required'}
        return self.render_json_response(context)

    def post(self, request, *args, **kwargs):
        """
        `request.POST` method is used to alter multiple resources in single
        request using AJAX.

        List of resources pks is passed in `pks` key as list of integers
        separated by comma.

        Only owned resources can be updated.

        Response contains status of removal and list of resource pks that
        were changed.
        """
        user = request.user
        data = request.POST.get('pks', None)
        custom_prefix = request.POST.get('custom_prefix', None)
        inherit_prefix = request.POST.get('append', False) == 'true'

        changed = []
        status = False
        msg = ''
        if data:
            values = parse_pks(pks=data)
            candidates = Resource.objects.filter(
                pk__in=values
            ).filter(
                (Q(owner=user) | Q(managers=user))
            )
            if candidates:
                if custom_prefix:
                    candidates.update(
                        custom_prefix=custom_prefix
                    )
                if inherit_prefix:
                    candidates = candidates.filter(
                        deployment__location__isnull=False
                    )
                    if candidates:
                        candidates.update(
                            inherit_prefix=inherit_prefix,
                        )
                status = True
            else:
                msg = 'No resources to update'
        else:
            msg = 'Invalid request'

        context = {'status': status, 'msg': msg}
        return self.render_json_response(context)


view_resource_define_prefix = ResourceDefinePrefixView.as_view()


class ResourceUpdateView(BaseUpdateView):
    """Resource update view."""

    template_name = 'storage/resources/resource_change.html'
    template_name_modal = 'storage/resources/resource_form.html'
    model = Resource
    raise_exception = True
    form_class = ResourceForm
    form_class_modal = SimpleResourceForm

view_resource_update = ResourceUpdateView.as_view()


class ResourceBulkUpdateView(BaseBulkUpdateView):
    """Resource bulk update view."""

    template_name = 'forms/simple_crispy_form.html'
    form_class = BulkUpdateResourceForm
    raise_exception = True
    tags_field = 'tags'


view_resource_bulk_update = ResourceBulkUpdateView.as_view()


class RateResourceView(LoginRequiredMixin, generic.FormView):
    """Resource rating view."""

    def post(self, request, *args, **kwargs):
        user = request.user
        rating = request.POST.get('rating')

        resource = Resource.objects.get(pk=request.POST.get('resource'))

        if rating > 0:
            user = UserProfile.objects.get(user=User.objects.get(username=user)).id

            if ResourceUserRate.objects.filter(resource_id=resource.pk, user=user).exists():
                rsc = ResourceUserRate.objects.get(resource_id=resource.pk, user=user)
                rsc.rating = rating
                rsc.save()
            else:
                ResourceUserRate.objects.create(
                    user_id=user,
                    resource_id=resource.pk,
                    rating=rating
                )
            if resource.rating:
                avg_rating = resource.rating.average
            else:
                avg_rating = 0
            return HttpResponse(json.dumps(
                {
                    'status': 'OK',
                    'avg_rating': str(avg_rating)
                }),
                content_type="application/json"
            )

        return HttpResponse(json.dumps(
            {'status': 'ERROR'}),
            content_type="application/json"
        )

view_rate_resource = RateResourceView.as_view()


class ResourceGenerateDataPackage(
        LoginRequiredMixin, generic.FormView, JSONResponseMixin
):
    """Generate data package with selected resources."""

    template_name = 'forms/simple_crispy_form.html'
    form_class = ResourceDataPackageForm
    raise_exception = True
    MAX_SIZE = getattr(settings, 'DATA_PACKAGE_MAX_SIZE', 10*1024*1024)

    def raise_exception_handler(self, request, *args, **kwargs):
        """For ajax requests if user is not authenticated, instead of
        redirection or access denied page, json with proper message is
        created"""
        context = {'success': False, 'msg': 'Authentication required'}
        return self.render_json_response(context)

    def form_valid(self, form):
        """
        """
        user = self.request.user
        resources = form.cleaned_data.get('resources', None)
        total_size = sum([k.file.size for k in resources])

        if not resources:
            msg = (
                'Nothing to process (most probably you have no permission '
                'to run this action on selected resources).'
            )
            context = {
                'success': False,
                'msg': msg,
            }
        elif total_size > self.MAX_SIZE:
            msg = (
                'We are sorry but the maximum size of a data package you can '
                'request for is {max_size} at the moment. The size of your current '
                'selection is {size}.'. format(
                    max_size=filesizeformat(self.MAX_SIZE),
                    size=filesizeformat(total_size)
                )
            )
            context = {
                'success': False,
                'msg': msg,
            }
        else:
            params = {
                'resources': resources,
                'user': user,
                'package_name': form.cleaned_data.get('package_name', None),
                'metadata': form.cleaned_data.get('metadata', None)
            }

            if settings.CELERY_ENABLED:
                task = celery_create_media_package.delay(**params)
                user_task = UserTask(
                    user=user,
                    task_id=task.task_id
                )
                user_task.save()
                msg = (
                    'You have successfully run the celery task. Your data package is '
                    'being generated now. '
                )
            else:
                msg = celery_create_media_package(**params)

            context = {
                'success': True,
                'msg': msg,
            }
        return self.render_json_response(context_dict=context)

    def form_invalid(self, form):
        """If form is not valid, form is re-rendered with error details,
        and message about unsuccessfull operation is shown"""
        context = {
            'success': False,
            'msg': 'Your form contain errors',
            'form_html': render_to_string(
                self.template_name,
                {'form': form},
                context_instance=RequestContext(self.request)
            )
        }
        return self.render_json_response(context_dict=context)


view_resource_data_package = ResourceGenerateDataPackage.as_view()


class ResourceSendfileMediaView(BaseServeFileView):

    authenticated_only = False

    field_map = {
        'pfile': 'file_preview',
        'efile': 'extra_file',
        'tfile': 'file_thumbnail',
        # It's not supported yet
        # 'etfile': 'extra_file_thumbnail',
    }

    def access_granted(self, resource, resource_field):
        field = self.field_map.get(resource_field, 'file')
        media_field = getattr(resource, field)
        if media_field:
            return self.serve_file(media_field.name)
        else:
            raise Http404

    def access_revoked(self):
        return self.serve_file(
            settings.RESOURCE_FORBIDDEN_THUMBNAIL, root=settings.STATIC_URL
        )

    def get(self, *args, **kwargs):
        resource_pk = kwargs.get('pk', None)
        resource_field = kwargs.get('field', None)

        if not (resource_pk and resource_field):
            raise Http404

        user = self.request.user

        resource = get_object_or_404(Resource, pk=resource_pk)
        status = resource.can_view(user=user, basic=True)
        if status:
            response = self.access_granted(
                resource=resource, resource_field=resource_field
            )
        else:
            response = self.access_revoked()
        return response

view_resource_sendfile_media = ResourceSendfileMediaView.as_view()
