# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib import messages
from django.views import generic
from django.core.urlresolvers import reverse
from django.utils.timezone import now
from django.template import RequestContext
from django.template.loader import render_to_string

from braces.views import (
    UserPassesTestMixin, JSONResponseMixin
)

from trapper.apps.geomap.models import Deployment
from trapper.apps.geomap.forms import (
    DeploymentForm, SimpleDeploymentForm, 
    BulkCreateDeploymentForm, BulkUpdateDeploymentForm,
    DeploymentImportForm
)
from trapper.apps.geomap.tasks import celery_import_deployments
from trapper.apps.common.views import (
    LoginRequiredMixin, BaseDeleteView, BaseUpdateView, 
    BaseBulkUpdateView
)
from trapper.apps.research.models import ResearchProject
from trapper.apps.accounts.models import UserTask


class DeploymentDetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    """View used for rendering details of specified deployment.

    Before details are rendered, permissions are checked and if currently
    logged in user has not enough permissions to view details,
    proper message is displayed.
    """
    template_name = 'geomap/deployment_detail.html'
    model = Deployment
    raise_exception = True

    def test_func(self, user):
        """
        Deployment details can be seen only if user has enough permissions
        """
        return self.get_object().can_view(user)

    def get_context_data(self, **kwargs):
        """Update context used to render template with data related to
        deployments
        """
        context = super(DeploymentDetailView, self).get_context_data(**kwargs)
        return context


view_deployment_detail = DeploymentDetailView.as_view()


class DeploymentListView(LoginRequiredMixin, generic.TemplateView):
    model = Deployment
    template_name = 'geomap/deployment_list.html'

    def get_context_data(self, **kwargs):
        """All we need to render base grid is:
        * Model name as title
        * Filter form instance

        This view is not serving any data. Data is read using DRF API
        """
        deployments = Deployment.objects.get_accessible()

        context = {
            'data_url': reverse('geomap:api-deployment-list'),
            'owners': deployments.order_by('owner__username').values_list(
                'owner__pk', 'owner__username'
            ).distinct(),
            'research_projects': ResearchProject.objects.get_accessible(
                user=self.request.user).distinct().values_list(
                    "pk", "acronym"
                ),
            'tags': Deployment.tags.values_list('pk', 'name'),
            'locations': deployments.values_list(
                "location__pk", "location__location_id"
            ).order_by('location__location_id'),
            'model_name': 'deployments',
            'update_redirect': False,
        }
        return {'deployment_context': context}


view_deployment_list = DeploymentListView.as_view()


class DeploymentCreateView(LoginRequiredMixin, generic.CreateView):
    """Deployment's create view.
    Handle the creation of the :class:`apps.geomap.models.Deployment` objects.
    """

    template_name = 'geomap/deployment_change.html'
    model = Deployment
    form_class = DeploymentForm

    def form_valid(self, form):
        """If form is valid then set `owner` as currently logged in user,
        and add message that deployment has been created"""
        user = self.request.user
        form.instance.owner = user
        messages.add_message(
            self.request,
            messages.SUCCESS,
            'New deployment has been successfully added'
        )
        self.object = form.save()
        self.object.tags.clear()
        for tag in form.cleaned_data['tags']:
            self.object.tags.add(tag)
        return super(DeploymentCreateView, self).form_valid(form)

    def form_invalid(self, form):
        """If form is not valid, form is re-rendered with error details,
        and message about unsuccessfull operation is shown"""
        messages.add_message(
            self.request,
            messages.ERROR,
            'Error creating new deployment'
        )
        return super(DeploymentCreateView, self).form_invalid(form)


view_deployment_create = DeploymentCreateView.as_view()


class DeploymentDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    deployments.

    Only deployments that user has enough permissions for can be deleted
    """
    model = Deployment
    protected_msg_tmpl = 'Deployment "{name}" can not be deleted. To \
    delete it you have to delete/unlink all resources that refer to \
    this deployment.'
    item_name_field = 'deployment_id'
    redirect_url = 'geomap:deployment_list'


view_deployment_delete = DeploymentDeleteView.as_view()


class DeploymentUpdateView(BaseUpdateView):
    """Deployment update view."""

    template_name = 'geomap/deployment_change.html'
    template_name_modal = 'geomap/deployment_form.html'
    model = Deployment
    raise_exception = True
    form_class = DeploymentForm
    form_class_modal = SimpleDeploymentForm
    item_name_field = 'deployment_id'

view_deployment_update = DeploymentUpdateView.as_view()


class DeploymentBulkUpdateView(BaseBulkUpdateView):
    """Deployment bulk update view."""

    template_name = 'forms/simple_crispy_form.html'
    form_class = BulkUpdateDeploymentForm
    raise_exception = True
    tags_field = 'tags'


view_deployment_bulk_update = DeploymentBulkUpdateView.as_view()


class DeploymentBulkCreateView(
        LoginRequiredMixin, generic.edit.FormView, JSONResponseMixin
):
    """Deployment bulk create view."""

    template_name = 'geomap/deployment_bulk_create_form.html'
    form_class = BulkCreateDeploymentForm

    def form_valid(self, form):
        """If form is valid then set `owner` as currently logged in user,
        and add message that deployments have been successfully created"""
        user = self.request.user
        deployment_list = []
        timestamp = now()
        managers = form.cleaned_data['managers']

        for location in form.cleaned_data['locations']:
            deployment = Deployment(
                location=location,
                deployment_code=form.cleaned_data['deployment_code'],
                start_date=form.cleaned_data['start_date'],
                end_date=form.cleaned_data['end_date'],
                research_project=form.cleaned_data['research_project'],
                owner=user,
                date_created=timestamp
            )
            deployment.deployment_id = "-".join(
                [deployment.deployment_code, location.location_id]
            )

            deployment_list.append(deployment)

        Deployment.objects.bulk_create(deployment_list)

        if managers:
            managers_through_list = []
            managers_through_model = Deployment.managers.through
            deployments_created_pks = Deployment.objects.filter(
                date_created=timestamp
            ).values_list('pk', flat=True)
            for deployment_pk in deployments_created_pks:
                for manager in managers:
                    managers_through_obj = managers_through_model(
                        deployment_id=deployment_pk,
                        user=manager
                    )
                    managers_through_list.append(managers_through_obj)
            managers_through_model.objects.bulk_create(managers_through_list)

        messages.add_message(
            self.request,
            messages.SUCCESS,
            '<strong>{n}</strong> new deployments have been successfully added.'.format(
                n=len(deployment_list)
            )
        )
        context = {
            'success': True,
            'msg': '',
            'url': reverse('geomap:deployment_list')
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

view_deployment_bulk_create = DeploymentBulkCreateView.as_view()


class DeploymentImportView(LoginRequiredMixin, generic.FormView):

    """Imports deployments from csv table.
    """

    template_name = 'geomap/deployment_import.html'
    form_class = DeploymentImportForm
    success_url = None

    def form_valid(self, form):
        """The form is valid so create/update deployment objects. At the end
        redirect to a list of deployments.
        """
        user = self.request.user
        params = {
            'data': form.cleaned_data,
            'user': user,
        }

        if settings.CELERY_ENABLED:
            task = celery_import_deployments.delay(**params)
            user_task = UserTask(
                user=user,
                task_id=task.task_id
            )
            user_task.save()
            msg = (
                'You have successfully run a celery task. Deployments '
                'are being imported now.'
            )
        else:
            msg = celery_import_deployments(**params)

        messages.success(
            request=self.request,
            message=msg
        )
        self.success_url = reverse(
            'accounts:dashboard'
        )
        return super(DeploymentImportView, self).form_valid(form)

view_deployment_import = DeploymentImportView.as_view()






