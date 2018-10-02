# -*- coding: utf-8 -*-
"""Extensions for views used in various applications"""

from django.views.generic import View, FormView, DetailView, UpdateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.conf import settings
from django.template import RequestContext
from django.template.loader import render_to_string

from braces.views import JSONResponseMixin, UserPassesTestMixin
from braces.views._access import AccessMixin
from bulk_update.helper import bulk_update
from taggit.models import Tag

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from trapper.apps.common.tools import parse_pks


class LoginRequiredMixin(AccessMixin):
    """
    View mixin which verifies that the user is authenticated.

    .. note::
        This should be the left-most mixin of a view, except when
        combined with CsrfExemptMixin - which in that case should
        be the left-most mixin.
    """
    raise_exception_handler = None

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated():
            if self.raise_exception:
                handler = self.raise_exception_handler
                if callable(handler):
                    return handler(request, *args, **kwargs)
                else:
                    raise PermissionDenied  # return a forbidden response
            else:
                return redirect_to_login(
                    request.get_full_path(),
                    self.get_login_url(),
                    self.get_redirect_field_name()
                )

        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class BaseListFilterDataView(JSONResponseMixin, View):
    """Base class for returning list of values that should be used
    to render form filters. Using this class removes need to
    mix angular code with django code in filters"""
    def get_filters_data(self):
        """Method used to return list of filter names and their values

        .. warning::
            To make this class usuable this method has to be overwritten"""
        return {}

    def get(self, request, *args, **kwargs):
        """Return json filter names and values that should be defined
        in :func:`get_filters_data` in inherited classes"""
        context = self.get_filters_data()
        return self.render_json_response(context_dict=context)


class HashedDetailView(DetailView):
    """Base detail view that operate on string hash instead of id/pk
    to select model instances

    By default used field is `hashcode`
    """
    hashcode_url_kwarg = 'hashcode'

    def get_object(self, queryset=None):
        """Return object from given model not by `pk` but using
        configurable `hashcode_url_kwarg` which by default is `hashcode`"""
        hashcode = self.kwargs.get(self.hashcode_url_kwarg, None)
        params = {self.hashcode_url_kwarg: hashcode}
        return get_object_or_404(self.model, **params)


class BaseDeleteView(LoginRequiredMixin, View, JSONResponseMixin):
    """Base view used for single or multiple object deletion
    Handle GET method (for single deletion) or POST (for single or multiple
    deletion)
    """

    http_method_names = ['get', 'post']

    raise_exception = True
    model = None
    protected_msg_tmpl = ''
    item_name_field = 'name'

    redirect_url = None

    def get_redirect_url(self):
        """Determine where to redirect"""
        return redirect(reverse(self.redirect_url))

    def get_model(self):
        return self.model

    def raise_exception_handler(self, request, *args, **kwargs):
        if request.is_ajax:
            context = {'status': False, 'msg': u'Authentication required'}
            return self.render_json_response(context)
        else:
            raise PermissionDenied

    def can_delete(self, item, user=None):
        """Delete access checker"""
        return item.can_delete(user=user)

    def add_message(self, status, template, item):
        """Create message for form handler.
        This method can be customized to modify i.e. default name attribute
        that is used in template"""
        messages.add_message(
            self.request,
            status,
            template.format(name=item.name)
        )

    def delete_item(self, item):
        item.delete()

    def bulk_delete(self, queryset):
        queryset.delete()

    def filter_editable(self, queryset, user):
        if getattr(self.model, 'managers', None):
            return queryset.filter(
                Q(owner=user) | Q(managers=user)
            )
        else:
            return queryset.filter(owner=user)

    def get(self, request, *args, **kwargs):
        """Delete objects based on GET request
        Object can be deleted only when can_delete returns True.

        This method is used to delete single object. PK of object is passed
        via GET argument (as part of url)
        """

        model = self.get_model()
        user = request.user
        item = get_object_or_404(model, pk=kwargs.get('pk', None))
        if self.can_delete(item=item, user=user):
            try:
                self.delete_item(item)
            except ProtectedError:
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    self.protected_msg_tmpl.format(
                        name=getattr(item, self.item_name_field, '')
                    )
                )
            else:
                messages.add_message(
                    self.request,
                    messages.SUCCESS,
                    u'{model_name} "{name}" has been deleted'.format(
                        model_name=self.model._meta.model_name.capitalize(),
                        name=getattr(item, self.item_name_field, '')
                    )
                )
            response = self.get_redirect_url()
        else:
            messages.add_message(
                self.request,
                messages.ERROR,
                u'You are not allowed to delete {model_name} "{name}".'.format(
                    model_name=self.model._meta.model_name.capitalize(),
                    name=getattr(item, self.item_name_field, '')
                )
            )
            if self.raise_exception:
                raise PermissionDenied
            else:
                response = self.get_redirect_url()
        return response

    def post(self, request, *args, **kwargs):
        """Delete multiple objects based on POST request. Object can be deleted
        only when request user has permission to do that.
        """
        user = request.user
        data = request.POST.get('pks', None)

        model = self.get_model()

        if data:
            values = parse_pks(pks=data)
            status = True
            msg = u''
            deleted = 0
            candidates = model.objects.filter(pk__in=values)
            candidates = self.filter_editable(
                candidates, user
            )

            total = len(candidates)

            if not total:
                status = False
                msg = (
                    u'No items to delete (most probably you have no permission '
                    u'to do that).'
                )
            else:
                try:
                    self.bulk_delete(candidates)
                    msg = str(total) +' record(s) have been successfully deleted.'
                except ProtectedError:
                    status = False
                    msg = (
                        u'Some of selected items can not be deleted because '
                        u'they are referenced through a protected foreign key. '
                        u'Unselect them and re-run the action.'
                    )
        else:
            status = False
            msg = u'Invalid request'

        context = {'status': status, 'msg': msg}
        return self.render_json_response(context)


class BaseUpdateView(
    LoginRequiredMixin, UserPassesTestMixin, UpdateView,
    JSONResponseMixin
):
    """
    Base update view.
    """

    template_name = None
    template_name_modal = None
    model = None
    raise_exception = True
    form_class = None
    form_class_modal = None
    item_name_field = 'name'

    def test_func(self, user):
        """Update is available only for users that have enough permissions"""
        return self.get_object().can_update(user)

    def get_template_names(self):
        if self.request.is_ajax():
            templates = [self.template_name_modal]
        else:
            templates = [self.template_name] 
        return templates

    def get_form_class(self):
        if self.request.is_ajax():
            if not self.form_class_modal:
                self.form_class_modal = self.form_class
            form_class = self.form_class_modal
        else:
            form_class = self.form_class
        return form_class

    def form_valid(self, form):
        success_msg = (
            u'{model_name} <strong>{name}</strong> has been '
            u'successfully updated.'.format(
                model_name=self.model._meta.model_name.capitalize(),
                name=getattr(form.instance, self.item_name_field)
            )
        )
        if self.request.is_ajax():
            self.object = form.save()
            context = {
                'success': True,
                'msg': success_msg
            }
            return self.render_json_response(context_dict=context)
        else:
            messages.add_message(
                self.request, messages.SUCCESS, success_msg,
            )
            return super(BaseUpdateView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            context = {
                'success': False,
                'msg': u'Your form contains errors.',
                'form_html': render_to_string(
                    self.template_name_modal,
                    {'form': form},
                    context_instance=RequestContext(self.request)
                )
            }
            return self.render_json_response(context_dict=context)
        else:
            messages.add_message(
                self.request, messages.ERROR,
                u'Your form contains errors.'
            )
            return super(BaseUpdateView, self).form_invalid(form)


class BaseBulkUpdateView(
    LoginRequiredMixin, FormView, JSONResponseMixin
):
    """
    """
    template_name = None
    form_class = None
    raise_exception = True
    tags_field = None

    def raise_exception_handler(self, request, *args, **kwargs):
        """For ajax requests if user is not authenticated, instead of
        redirection or access denied page, json with proper message is
        created"""
        context = {'success': False, 'msg': u'Authentication required'}
        return self.render_json_response(context)

    def update_extra_m2m_fields(self, records, m2m_data):
        return

    def form_valid(self, form):
        """
        """
        form.cleaned_data.pop('records_pks', None)
        records = form.cleaned_data.pop('records', None)
        if not records:
            msg = (
                'Nothing to process (most probably you have no permission '
                'to run this action on selected records)'
            )
            context = {
                'success': False,
                'msg': msg,
            }
        else:
            # get model
            model = form.Meta.model
            model_name = model._meta.model_name
            # get m2m fields of given model
            m2m_fields = [
                k[0].name for k in model._meta.get_m2m_with_model()
            ]
            basic_data = {}
            m2m_data = {}

            # check if tags field and data available
            tags2add = form.cleaned_data.pop('tags2add', None)
            tags2remove = form.cleaned_data.pop('tags2remove', None)

            if self.tags_field and (tags2add or tags2remove):
                tags_through_model = getattr(model, self.tags_field).through

                if tags2add:
                    tags_through_to_create = []
                    tags = []
                    # get_or_create `Tag` objects for provided tag names
                    for tag in tags2add:
                        obj = Tag.objects.get_or_create(name=tag)
                        tags.append(obj[0])

            # split posted data into 2 dicts
            for field in form.cleaned_data:
                if field in m2m_fields:
                    m2m_data[field] = form.cleaned_data[field]
                else:
                    model_field = model._meta.get_field(field)
                    if model_field.get_internal_type() == 'ForeignKey':
                        if form.cleaned_data[field]:
                            basic_data[field+'_id'] = form.cleaned_data[field].pk
                        else:
                            basic_data[field+'_id'] = None
                    else:
                        basic_data[field] = form.cleaned_data[field]

            to_update = []

            managers = m2m_data.pop('managers', None)
            if managers:
                managers_through_model = getattr(
                    model, 'managers').through
                managers_to_update = []

            records_pks = []
            for obj in records:
                records_pks.append(obj.pk)

                if basic_data:
                    for field in basic_data:
                        setattr(obj, field, basic_data[field])
                    to_update.append(obj)

                if managers:
                    for m in managers:
                        managers_through_obj = managers_through_model(
                            user=m
                        )
                        setattr(managers_through_obj, model_name, obj)
                        managers_to_update.append(managers_through_obj)

                if self.tags_field and tags2add:
                    for tag in tags:
                        tags_through_obj = tags_through_model(
                            tag=tag, content_object_id=obj.pk
                        )
                        tags_through_to_create.append(tags_through_obj)

            if basic_data:
                bulk_update(
                    to_update, update_fields=basic_data.keys()
                )

            if managers:
                managers_through_model.objects.filter(**{
                    model_name +'__in': records
                }).delete()
                managers_through_model.objects.bulk_create(
                    managers_to_update
                )

            if self.tags_field and tags2remove:
                # remove specified tags (actually we only remove
                # the objects of the "through" model i.e. `TaggedItem`)
                tags_through_model.objects.filter(
                    tag__name__in=tags2remove,
                    content_object_id__in=records_pks
                ).delete()


            if self.tags_field and tags2add:
                # delete already existing TaggedItems to avoid duplicated records
                tags_through_model.objects.filter(
                    tag__in=tags, content_object_id__in=records_pks
                )

                # create new TaggedItems
                tags_through_model.objects.bulk_create(
                    tags_through_to_create
                )

            # now bulk update extra m2m fields
            self.update_extra_m2m_fields(records, m2m_data)

            msg = (
                'You have successfully updated <strong>{n}</strong> records.'.format(
                    n=len(records)
                )
            )
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
