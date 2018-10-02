# -*- coding: utf-8 -*-
"""
Views used to handle logic related to collection management in storage
application
"""
from __future__ import unicode_literals

import os

from django.db.models import Q
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse_lazy, reverse
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.template import RequestContext
from django.template.loader import render_to_string

from formtools.wizard.views import SessionWizardView
from braces.views import UserPassesTestMixin, JSONResponseMixin

from trapper.apps.common.views import LoginRequiredMixin
from trapper.apps.common.tools import parse_pks, datetime_aware
from trapper.apps.common.views import (
    BaseDeleteView, BaseUpdateView, BaseBulkUpdateView
)
from trapper.apps.storage.models import Collection, Resource
from trapper.apps.storage.tasks import celery_process_collection_upload
from trapper.apps.storage.forms import (
    CollectionForm, CollectionRequestForm, CollectionUploadConfigForm,
    CollectionUploadDataForm, BulkUpdateCollectionForm
)
from trapper.apps.messaging.models import (
    Message, CollectionRequest
)
from trapper.apps.messaging.taxonomies import MessageType
from trapper.apps.research.models import ResearchProject
from trapper.apps.storage.views.resource import ResourceGridContextMixin
from trapper.apps.accounts.utils import (
    create_external_media
)
from trapper.apps.accounts.models import UserTask
from trapper.apps.geomap.models import MapManagerUtils

User = get_user_model()


class CollectionGridContextMixin(object):
    """
    """

    def get_collection_url(self, **kwargs):
        """Return standard DRF API url for collections"""
        return reverse('storage:api-collection-list')

    def get_collection_delete_url(self, **kwargs):
        """Return standard url used for removing multiple collections"""
        return reverse('storage:collection_delete_multiple')

    def get_collection_context(self, **kwargs):
        """Build collection context"""
        context = {
            'research_projects': ResearchProject.objects.get_accessible(
                user=self.request.user).values_list('pk', 'name'),
            'owners': User.objects.filter(
                owned_collections__isnull=False
            ).distinct(),
            'data_url': self.get_collection_url(**kwargs),
            'collection_delete_url': self.get_collection_delete_url(**kwargs),
            'maps': MapManagerUtils.get_accessible(user=self.request.user),
            'model_name': 'collections',
            'update_redirect': False,
        }
        return context


class CollectionListView(
        LoginRequiredMixin, generic.TemplateView, CollectionGridContextMixin
):
    """View used for rendering template with collection grid.
    Context of view is updated with :class:`CollectionGridContextMixin`
    """
    model = Collection
    template_name = 'storage/collections/collection_list.html'

    def get_context_data(self, **kwargs):
        """All we need to render base grid is:
        * Model name as title
        * Filter form instance
        * Hide classification project add action

        This view is not serving any data. Data is read using DRF API
        """
        context = super(CollectionListView, self).get_context_data(**kwargs)
        context['collection_context'] = self.get_collection_context(**kwargs)
        return context


view_collection_list = CollectionListView.as_view()


class CollectionOnDemandListView(CollectionListView):
    """View used for rendering template with ondemand collections grid.
    """
    template_name = 'storage/collections/collection_ondemand_list.html'

    def get_context_data(self, **kwargs):
        context = super(CollectionOnDemandListView, self).get_context_data(**kwargs)
        context['collection_context']['data_url'] = reverse(
            'storage:api-collection-ondemand-list'
        )
        return context


view_collection_ondemand_list = CollectionOnDemandListView.as_view()


class CollectionDetailView(
        LoginRequiredMixin, UserPassesTestMixin, generic.DetailView, 
        ResourceGridContextMixin
):
    """View used for rendering details of specified collection.

    Before details are rendered, permissions are checked and if currently
    logged in user has not enough permissions to view details,
    proper message is displayed.

    This view uses
    :class:`apps.storage.views.resources.ResourceGridContextMixin`
    for altering behaviour resource grid rendered in details
    """

    template_name = 'storage/collections/collection_detail.html'
    model = Collection
    raise_exception = True
    context_object_name = 'collection'

    def test_func(self, user):
        """
        Collection details can be seen only if user has enough permissions
        """
        return self.get_object().can_view(user)

    def get_resource_url(self, **kwargs):
        """Alter url for resources DRF API, to get only resources that
        belongs to collection and are accessible for currently logged in
        user"""
        collection = kwargs.get('collection')
        return '{url}?collections={pk}'.format(
            url=reverse('storage:api-resource-list'),
            pk=collection.pk
        )

    def get_context_data(self, **kwargs):
        """
        Alter context data used for resources grid in collection details:

        * hide create collection action
        * hide filter by collections
        * hide resource delete action
        * hide resource update action
        """
        context = super(CollectionDetailView, self).get_context_data(**kwargs)

        collection = context['object']
        context['resource_context'] = self.get_resource_context(
            collection=collection
        )
        deployments = context['resource_context']['deployments']
        context['resource_context']['deployments'] = deployments.filter(
            resources__collection=collection).distinct()
        context['resource_context']['hide_create_collection'] = True
        context['resource_context']['hide_filter_collection'] = True
        #context['resource_context']['hide_delete'] = True
        #context['resource_context']['hide_update'] = True
        context['resource_context']['collection_pk'] = collection.pk
        if not collection.can_update(user=self.request.user):
            context['resource_context']['hide_change_actions'] = True
        return context


view_collection_detail = CollectionDetailView.as_view()


class CollectionCreateView(
    LoginRequiredMixin, generic.CreateView, JSONResponseMixin
):
    """Collection's create view.
    Handle the creation of the :class:`apps.storage.models.Collection` objects.
    """
    template_name = 'storage/collections/collection_create.html'
    model = Collection
    form_class = CollectionForm

    def form_valid(self, form):
        """If form is valid then set `owner` as currently logged in user,
        and add message that collection has been created"""
        user = self.request.user
        form.instance.owner = user
        messages.add_message(
            self.request,
            messages.SUCCESS,
            'New collection <strong>{name}</strong> has been added'.format(
                name=form.instance.name
            )
        )
        self.object = form.save()
        context = {
            'success': True,
            'msg': '',
            'url': reverse(
                'storage:collection_detail', kwargs={'pk': self.object.pk}
            )
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

view_collection_create = CollectionCreateView.as_view()


class CollectionUpdateView(BaseUpdateView):
    """Collection update view.
    It handles the update of the :class:`apps.storage.models.Collection` objects.
    """
    template_name = 'storage/collections/collection_update.html'
    template_name_modal = 'storage/collections/collection_update_modal.html'
    model = Collection
    raise_exception = True
    form_class = CollectionForm

view_collection_update = CollectionUpdateView.as_view()


class CollectionUploadWizardView(LoginRequiredMixin, SessionWizardView):
    """
    Wizard view used to handle an upload of a collection's definition 
    (YAML) and data (ZIP archive) files. However, this view does not directly 
    create any collection or resource objects; instead it runs a celery task
    If the `settings.CELERY_ENABLED` is set to True a task is run in the 
    asynchronous mode.
    """
    form_list = [CollectionUploadConfigForm, CollectionUploadDataForm]
    template_names = [
        'storage/collections/collection_upload_config.html',
        'storage/collections/collection_upload_data.html'
    ]

    file_storage = FileSystemStorage(
        location=os.path.join(settings.CELERY_DATA_ROOT, 'collections')
    )

    def get(self, request, *args, **kwargs):
        """Make sure that when entering this view, user's external media
        directory exists."""
        create_external_media(username=request.user.username)
        return super(CollectionUploadWizardView, self).get(
            request, *args, **kwargs
        )

    def get_template_names(self):
        """Each step of this wizard has its own template."""
        return self.template_names[self.get_step_index()]

    def done(self, form_list, **kwargs):
        """When all steps of this wizard are completed successfully a context
        data is passed to a celery task.
        """

        user= self.request.user
        params = {
            'definition_file': form_list[0].cleaned_data['definition_file'],
            'owner': user,
        }
        archive_file = form_list[1].cleaned_data.get('archive_file')
        uploaded_media = form_list[1].cleaned_data.get('uploaded_media')

        if archive_file:
            params['archive_file'] = archive_file
        else:
            params['archive_file'] = uploaded_media

        if settings.CELERY_ENABLED:
            task = celery_process_collection_upload.delay(**params)
            user_task = UserTask(
                user=user,
                task_id=task.task_id
            )
            user_task.save()
            msg = (
                'You have successfully run the celery task. Your uploaded data '
                'package is being processed now. '
            )
            success_url = reverse('accounts:dashboard')
        else:
            msg = celery_process_collection_upload(**params)
            success_url = reverse('storage:collection_list')

        messages.success(
            request=self.request,
            message=msg
        )
        
        return redirect(success_url)

view_collection_upload = CollectionUploadWizardView.as_view()


class CollectionRequestView(LoginRequiredMixin, generic.FormView):
    """
    """

    success_url = reverse_lazy('storage:collection_list')
    template_name = "storage/collections/collection_request.html"
    form_class = CollectionRequestForm

    # Template of the request message
    TEXT_TEMPLATE = (
        'Dear {owner},<br><br>I would like to ask you for the permission '
        'to use the following collection:<br>'
        '<a href="{collection_url}">{collection_url}</a>.<br><br>'
        'Best regards,<br>{user}'
    )

    def get_context_data(self, *args, **kwargs):
        """Update the context with selected collection and informations
        about current request (e.g. not possible as a user has already asked for
        the access to this collection in the last 24h)"""
        context = super(CollectionRequestView, self).get_context_data(**kwargs)

        user = self.request.user

        # self.collection was set previously in the "get_initial" method
        context['collection'] = self.collection
        context.update(
            Collection.objects.api_ask_access_context(
                item=self.collection, user=user
            )
        )
        return context

    def get_initial(self, *args, **kwargs):
        """Initialize the form with the projects query, as well as the
        collection in question.
        """
        self.collection = get_object_or_404(Collection, pk=self.kwargs['pk'])
        collection_full_url = self.request.build_absolute_uri(
            reverse(
                'storage:collection_detail', kwargs={'pk': self.collection.pk}
            )
        )
        initial = {
            'object_pk': self.collection.pk,
            'text': self.TEXT_TEMPLATE.format(
                owner=self.collection.owner.username,
                collection_url=collection_full_url,
                user=self.request.user.username 
            )
        }
        return initial

    def form_valid(self, form):
        """Create a :class:`apps.messaging.models.Message`
        and :class:`apps.messaging.models.CollectionRequest`
        objects directed to the owner of the collection.
        """
        collection = get_object_or_404(
            Collection, pk=form.cleaned_data['object_pk']
        )
        project = form.cleaned_data['project']
        msg = Message.objects.create(
            subject="Request for collections",
            text=form.cleaned_data['text'],
            user_from=self.request.user,
            user_to=collection.owner,
            date_sent=datetime_aware(),
            message_type=MessageType.COLLECTION_REQUEST
        )
        coll_req = CollectionRequest(
            name="Request for collections",
            user=collection.owner,
            user_from=self.request.user,
            message=msg,
            project=project
        )
        coll_req.save()
        coll_req.collections.add(collection)

        # send email to the owner of the collection
        if collection.owner.userprofile.system_notifications:
            send_mail(
                subject='Request for one of your collections',
                message=form.cleaned_data['text'],
                from_email=None,
                recipient_list=[collection.owner.email],
                fail_silently=True
            )

        messages.add_message(
            self.request,
            messages.SUCCESS,
            (
                'Your request for the collection <strong>{name}</strong> has been '
                'successfully submitted.'
            ).format(
                name=collection.name
            )
        )
        return super(CollectionRequestView, self).form_valid(form)

    def form_invalid(self, form):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        messages.add_message(
            self.request,
            messages.ERROR,
            'Error creating collection request'
        )
        return super(CollectionRequestView, self).form_invalid(form)


view_collection_request = CollectionRequestView.as_view()


class CollectionDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    colletions.

    Only collections that user has enough permissions for can be deleted
    """

    model = Collection
    redirect_url = 'storage:collection_list'


view_collection_delete = CollectionDeleteView.as_view()


class CollectionResourceDeleteView(
    LoginRequiredMixin, generic.View, JSONResponseMixin
):
    """This view is used to remove resources from collection.

    User is required to have at least access permissions for each resource that
    is removed from a collection.

    .. note::
        Only relation Resource <-> Collection is removed. Resources are not
        removed from a database.
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
        `request.POST` method is used to remove multiple resources
        from collection in a single request using AJAX.
        """
        user = request.user
        data = request.POST.get('pks', None)

        try:
            collection = Collection.objects.get(
                pk=kwargs.get('pk', None)
            )
        except Collection.DoesNotExist:
            collection = None

        changed = []
        if data and collection and collection.can_update(user=user):
            values = parse_pks(pks=data)
            status = True
            msg = ''
            collection.resources.through.objects.filter(
                resource__in=values, collection=collection.pk
            ).delete()
        else:
            status = False
            msg = 'Invlid request'

        context = {'status': status, 'msg': msg}
        return self.render_json_response(context)

view_collection_resource_delete = CollectionResourceDeleteView.as_view()


class CollectionResourceAppendView(LoginRequiredMixin, generic.View):
    """This view is used to append list of resources to collection.

    User is required to have at least access permissions for each resource that
    is added to collection.
    """

    raise_exception = True

    def post(self, request, *args, **kwargs):
        """
        `request.POST` method is used to append multiple resources
        to collection in single request.

        List of resources pks is passed in `pks` key as list of integers
        separated by comma.

        Before append, all resources pks are validated if user can view
        them and only those, which user has enough permissions for, are
        added to collection.

        Response contains status of update and list of resource pks that
        were added.

        After that, user is redirected to collection details.
        """
        user = request.user
        collection_pk = request.POST.get('collection', None)
        resources_pk = request.POST.get('resources', None)
        app = request.POST.get('app', None)
        resources_url = reverse('storage:resource_list')
        resources = None

        if resources_pk:
            resources_pk = parse_pks(pks=resources_pk)
            if app == 'media_classification':
                base_queryset = Resource.objects.filter(
                    classifications__pk__in=resources_pk
                )
            else:
                base_queryset=Resource.objects.filter(
                    pk__in=resources_pk
                )
            resources = Resource.objects.get_accessible(
                base_queryset=base_queryset
            )

        if not resources:
            messages.error(
                request,
                'You have no permissions to add any of selected resources.'
            )
            return redirect(resources_url)

        collection = get_object_or_404(Collection, pk=collection_pk)
        collection_url = reverse(
            'storage:collection_detail', kwargs={'pk': collection.pk}
        )

        if not collection.can_update(user=user):
            messages.error(
                request, 'You have no permissions to modify this collection.'
            )
            return redirect(resources_url)

        if not collection.status == 'Private':
            n = resources.exclude(
                Q(owner=user) | Q(managers=user)
            ).count()
            if n != 0:
                messages.error(
                    request,
                    'You have no permission to add some of selected resources '
                    'to this "{ctype}" collection'.format(
                        ctype = collection.status.lower()
                    )                
                )
                return redirect(resources_url)

        new_resources = resources.exclude(
            pk__in=collection.resources.values_list('pk', flat=True)
        )

        if not new_resources:
            messages.warning(
                request,
                'The selected resources already are in this collection.'
            )
            return redirect(collection_url)

        messages.success(
            request,
            'You have successfully added <strong>{len}</strong> new '
            'resources to this collection.'.format(
                len=new_resources.count()
            )
        )

        collection.resources.add(*new_resources)
        return redirect(collection_url)


view_collection_resource_append = CollectionResourceAppendView.as_view()


class CollectionBulkUpdateView(BaseBulkUpdateView):
    """Collection bulk update view."""

    template_name = 'forms/simple_crispy_form.html'
    form_class = BulkUpdateCollectionForm
    raise_exception = True


view_collection_bulk_update = CollectionBulkUpdateView.as_view()


class CollectionResourcesDeleteOrphanedView(
        LoginRequiredMixin, UserPassesTestMixin, generic.View
):
    """
    """
    raise_exception = True

    def get_object(self):
        return get_object_or_404(Collection, pk=self.kwargs['pk'])

    def test_func(self, user):
        return self.get_object().can_update(user)

    def get(self, *args, **kwargs):
        obj = self.get_object()
        user = self.request.user
        resources_pks = obj.get_orphaned_resources(user=user)
        resources = Resource.objects.filter(pk__in=resources_pks)
        for resource in resources:
            obj.resources.remove(resource)
        collection_url = reverse(
            'storage:collection_detail', kwargs={'pk': obj.pk}
        )
        messages.success(
            self.request,
            'Unaccessable resources have been successfully removed from this collection.'
        )
        return redirect(collection_url)


view_collection_resource_delete_orphaned = CollectionResourcesDeleteOrphanedView.as_view()
