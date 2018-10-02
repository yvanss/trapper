# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.conf import settings
from django.views import generic
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model

from leaflet_storage.views import MapDetailMixin, MapView, MapCreate
from leaflet_storage.forms import AnonymousMapPermissionsForm
from leaflet_storage.views import simple_json_response, render_to_json
from leaflet_storage.models import Map

from trapper.apps.geomap.forms import UpdateMapPermissionsForm
from trapper.apps.common.views import LoginRequiredMixin, BaseDeleteView
from trapper.apps.accounts.utils import get_pretty_username
from trapper.apps.media_classification.models import ClassificationProject

User = get_user_model()


class MapListView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'geomap/map_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'data_url': reverse('geomap:api-map-list'),
            'owners': set([
                get_pretty_username(user=user) for user in
                User.objects.exclude(owned_maps__isnull=True)
            ]),
            'model_name': 'maps'
        }
        return {'map_context': context}

view_map_list = MapListView.as_view()


class UpdateMapPermissions(LoginRequiredMixin, generic.UpdateView):

    """View for custom map permissions update"""
    template_name = "geomap/map_update_permissions.html"
    model = Map
    pk_url_kwarg = 'map_id'
    form_class = UpdateMapPermissionsForm

    def get_form_class(self):
        if self.object.owner:
            return self.form_class
        else:
            return AnonymousMapPermissionsForm

    def get_form(self, form_class=None):
        form = super(UpdateMapPermissions, self).get_form(form_class)
        user = self.request.user
        if self.object.owner and not user == self.object.owner:
            del form.fields['edit_status']
            del form.fields['share_status']
        return form

    def get_form_kwargs(self):
        """ Setting kwargs owner for use inside form
        to filter choices"""
        kwargs = super(UpdateMapPermissions, self).get_form_kwargs()
        kwargs['owner'] = self.object.owner
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        return simple_json_response(
            info="Map editors updated with success!"
        )

    def render_to_response(self, context, **response_kwargs):
        return render_to_json(
            self.get_template_names(),
            response_kwargs,
            context,
            self.request
        )

view_update_map_permissions = UpdateMapPermissions.as_view()


class TrapperNewMapView(LoginRequiredMixin, MapDetailMixin, generic.TemplateView):
    template_name = "geomap/map_detail.html"

    def is_edit_allowed(self):
        if self.request.user.is_authenticated():
            return True
        return False

    def get_storage_id(self):
        if not self.request.user.is_authenticated():
            return True
        else:
            return None

    def get_context_data(self, **kwargs):
        context = super(TrapperNewMapView, self).get_context_data(**kwargs)
        properties = {}
        if not self.is_edit_allowed():
            properties['datalayersControl'] = False
        map_settings = json.loads(context['map_settings'])
        map_settings['properties'].update(properties)
        context['map_settings'] = json.dumps(
            map_settings, indent=settings.DEBUG)
        context['classification_projects'] = \
            ClassificationProject.objects.get_accessible(
                user=self.request.user
            )
        return context

view_new_map = TrapperNewMapView.as_view()


class TrapperMapView(LoginRequiredMixin, MapView):
    template_name = "geomap/map_detail.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.can_view(request):
            return HttpResponseForbidden('Forbidden')
        return super(MapView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TrapperMapView, self).get_context_data(**kwargs)
        context['classification_projects'] = \
            ClassificationProject.objects.get_accessible(
                user=self.request.user
            )
        return context

view_map = TrapperMapView.as_view()


class TrapperMapDeleteView(BaseDeleteView):

    model = Map
    item_name_field = 'map_id'
    redirect_url = 'geomap:map_list'

view_map_delete = TrapperMapDeleteView.as_view()


class TrapperMapCreateView(LoginRequiredMixin, MapCreate):

    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()
        msg = ("Congratulations, your map has been created!")
        url = self.object.get_absolute_url()
        response = simple_json_response(
            id=self.object.pk,
            url='/geomap'+url,
            info=msg
        )
        return response

view_map_create = TrapperMapCreateView.as_view()
