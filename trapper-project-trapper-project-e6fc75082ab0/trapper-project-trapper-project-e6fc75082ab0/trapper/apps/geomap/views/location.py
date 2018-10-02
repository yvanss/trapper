# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib import messages
from django.http import (
    HttpResponseForbidden, HttpResponseNotFound,
)
from django.views import generic
from django.core.urlresolvers import reverse
from django.template.context_processors import csrf
from django.utils.translation import ugettext as _

from braces.views import (
    JSONResponseMixin, AjaxResponseMixin
)
from crispy_forms.utils import render_crispy_form

from trapper.apps.geomap.models import Location, MapManagerUtils
from trapper.apps.storage.models import Collection
from trapper.apps.geomap.forms import (
    LocationImportForm, LocationFilterForm, CreateLocationForm,
    BulkUpdateLocationForm
)
from trapper.apps.geomap.tasks import celery_import_locations
from trapper.apps.common.views import (
    LoginRequiredMixin, BaseDeleteView, BaseBulkUpdateView
)
from trapper.apps.accounts.models import UserTask
from trapper.apps.research.models import ResearchProject


class LocationListView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'geomap/location_list.html'

    def get_context_data(self, **kwargs):
        """All we need to render base grid is:
        * Model name as title
        * Filter form instance

        This view is not serving any data. Data is read using DRF API
        """
        locations = Location.objects.get_available()

        context = {
            'data_url' : reverse('geomap:api-location-list'),
            'owners': locations.order_by('owner__username').values_list(
                'owner__pk', 'owner__username'
            ).distinct(),
            'maps': MapManagerUtils.get_accessible(user=self.request.user),
            'research_projects': ResearchProject.objects.get_accessible(
                user=self.request.user).distinct().values_list(
                    "pk", "acronym"
                ),
            'countries': set(locations.filter(
                country__isnull=False
            ).values_list('country', flat=True).distinct()),
            'model_name': 'locations',
        }
        return {'location_context': context}

view_location_list = LocationListView.as_view()


class LocationImportView(LoginRequiredMixin, generic.FormView):

    """Uploads location data from csv or gpx file.
    """

    template_name = 'geomap/location_import.html'
    form_class = LocationImportForm
    success_url = None

    def form_valid(self, form):
        """Attaches a message once the form was validated."""

        user = self.request.user
        params = {
            'data': form.cleaned_data,
            'user': user,
        }

        if settings.CELERY_ENABLED:
            task = celery_import_locations.delay(**params)
            user_task = UserTask(
                user=user,
                task_id=task.task_id
            )
            user_task.save()
            msg = (
                'You have successfully run a celery task. Locations '
                'are being imported now.'
            )
        else:
            msg = celery_import_locations(**params)

        messages.success(
            request=self.request,
            message=msg
        )
        self.success_url = reverse(
            'accounts:dashboard'
        )
        return super(LocationImportView, self).form_valid(form)


view_location_import = LocationImportView.as_view()


class LocationFilterFormView(
    LoginRequiredMixin, JSONResponseMixin, AjaxResponseMixin, 
    generic.View
):

    def get_ajax(self, request, *args, **kwargs):
        location_form = render_crispy_form(
            LocationFilterForm(request.GET),
            context=request
        )
        context = {'location_form_html': location_form}
        return self.render_json_response(context)


view_location_filter_form = LocationFilterFormView.as_view()


# get names of requested collections
class LocationCollectionAjaxView(
    LoginRequiredMixin, JSONResponseMixin, AjaxResponseMixin, 
    generic.View
):

    def get_ajax(self, request, *args, **kwargs):
        qs = Collection.objects.filter(
            pk__in=request.GET['collections'].split(',')
        ).values('pk', 'name').order_by('name')
        return self.render_json_response(list(qs))


view_location_collections = LocationCollectionAjaxView.as_view()


class LocationCreateFormView(
    LoginRequiredMixin, JSONResponseMixin, AjaxResponseMixin, 
    generic.View
):

    def get_ajax(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseForbidden(
                _('You are not allowed to add new locations.'))
        location_form = render_crispy_form(
            CreateLocationForm(),
            context=csrf(request))
        return self.render_json_response(
            {'location_form_html': location_form}
        )

    def post_ajax(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseForbidden(
                _('You are not allowed to add new locations.'))
        form = CreateLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.owner = request.user
            location.save()
            form.save_m2m()
            return self.render_json_response(
                {'success': True,
                 'id': location.pk}
            )
        else:
            form = render_crispy_form(form, context=csrf(request))
            return self.render_json_response(
                {'location_form_html': form}
            )

view_location_create_form = LocationCreateFormView.as_view()


class LocationEditFormView(
    LoginRequiredMixin, JSONResponseMixin, AjaxResponseMixin,
    generic.View
):

    def get_ajax(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        try:
            location = Location.objects.get_available().get(pk=pk)
        except Location.DoesNotExist:
            return HttpResponseNotFound(_("There is no location with this ID."))
        if not location.can_update(request.user):
            return HttpResponseForbidden(
                _('You are not allowed to edit this location.'))
        location_form = render_crispy_form(
            CreateLocationForm(request=request, instance=location),
            context=csrf(request)
        )
        return self.render_json_response(
            {'location_form_html': location_form}
        )

    def post_ajax(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            location = Location.objects.get_available().get(pk=pk)
        except Location.DoesNotExist:
            return HttpResponseNotFound(_("There is no location with this ID."))
        if not location.can_update(request.user):
            return HttpResponseForbidden(
                _('You are not allowed to edit this location.'))
        form = CreateLocationForm(request.POST, request=request,
                                  instance=location)
        if form.is_valid():
            form.save()
            return self.render_json_response(
                {'success': True}
            )
        else:
            form = render_crispy_form(form, context=csrf(request))
            return self.render_json_response(
                {'location_form_html': form}
            )

view_location_edit_filter_form = LocationEditFormView.as_view()


class LocationDeleteView(BaseDeleteView):

    model = Location
    protected_msg_tmpl = 'Location "{name}" can not be deleted. To \
    delete it you have to first delete/unlink all deployments that refer to \
    this location.'
    item_name_field = 'location_id'
    redirect_url = 'geomap:location_list'


view_location_delete = LocationDeleteView.as_view()


class LocationBulkUpdateView(BaseBulkUpdateView):
    """Location bulk update view."""

    template_name = 'forms/simple_crispy_form.html'
    form_class = BulkUpdateLocationForm
    raise_exception = True


view_location_bulk_update = LocationBulkUpdateView.as_view()
