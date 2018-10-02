# -*- coding: utf-8 -*-
"""
Views used to handle logic related to classificator management in media
classification application
"""
from __future__ import unicode_literals

from django.shortcuts import redirect
from django.views import generic
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from braces.views import UserPassesTestMixin

from trapper.apps.media_classification.models import (
    Classificator
)
from trapper.apps.media_classification.forms import (
    PredefinedAttributeForm, CustomAttributeForm, ClassificatorForm
)
from trapper.apps.media_classification.taxonomy import ClassificatorSettings
from trapper.apps.common.views import LoginRequiredMixin, BaseDeleteView

User = get_user_model()


class ClassificatorGridContextMixin(object):
    """Mixin used with views that use any classificator listing
    for changing list behaviour.
    This mixin can be used to:

    * change classificator url (i.e. add filtering)
    """
    def get_classificator_url(self, **kwargs):
        """Return standard DRF API url for classificators"""
        return reverse('media_classification:api-classificator-list')

    def get_classificator_context(self, **kwargs):
        """Build classificator context"""
        context = {
            'data_url': self.get_classificator_url(**kwargs),
            'owners': User.objects.filter(
                user_classificators__isnull=False
            ).distinct(),
            'model_name': 'classificators',
            'update_redirect': 'true'
        }
        return context


class ClassificatorListView(
    LoginRequiredMixin, generic.ListView, ClassificatorGridContextMixin
):
    """List view of the
    :class:`apps.media_classification.models.Classificator` instances.

    This view does not require any special permissions and can be viewed
    even by anonymous users.
    """
    model = Classificator
    context_object_name = 'classificators'
    template_name = 'media_classification/classificators/list.html'

    def get_context_data(self, **kwargs):
        """Update context used to render template with classificator context
        and owners used for filtering"""
        context = {
            'classificator_context': self.get_classificator_context(),
        }
        return context

view_classificator_list = ClassificatorListView.as_view()


class ClassificatorAttributesMixin(object):

    def process_item(self, item, attributes, custom_attrs):
        """For each attribute render config that will be used in
        template to render proper form fields"""
        is_custom_attr = item in custom_attrs

        if is_custom_attr:
            field_type = custom_attrs[item]['field_type']
            item_type = ClassificatorSettings.FIELD_LABELS[field_type]
            item_cls = 'label-default'
            item_hstore = self.object.custom_attrs[item]
        else:
            item_type = 'PREDEFINED'
            item_cls = 'label-default'
            item_hstore = ''

        attributes.append({
            'name': item,
            'type': item_type,
            'cls': item_cls,
            'hstore': item_hstore,
            'is_custom': is_custom_attr,
        })

    def set_attributes_context(self, obj):
        custom_attrs = obj.parse_hstore_values('custom_attrs')
        static_order = obj.static_attrs_order
        dynamic_order = obj.dynamic_attrs_order

        self.attributes_dynamic = []
        self.attributes_static = []
        if static_order:
            for item in static_order.split(','):
                self.process_item(
                    item=item,
                    attributes=self.attributes_static,
                    custom_attrs=custom_attrs
                )

        if dynamic_order:
            for item in dynamic_order.split(','):
                self.process_item(
                    item=item,
                    attributes=self.attributes_dynamic,
                    custom_attrs=custom_attrs
                )


class ClassificatorDetailView(
        LoginRequiredMixin, ClassificatorAttributesMixin,
        generic.DetailView
):
    """View used for rendering details of specified classificator.

    This view contain well formatted predefined and custom attributes
    and can be seen by all users (including anonymous)
    """
    model = Classificator
    context_object_name = 'classificator'
    template_name = 'media_classification/classificators/detail.html'

    def get_context_data(self, **kwargs):
        """Update context used to render template with predefined and custom
        attributes from given classificator"""
        context = super(
            ClassificatorDetailView, self
        ).get_context_data(**kwargs)
        classificator = context['object']

        self.set_attributes_context(classificator)
        context['attributes_dynamic'] = self.attributes_dynamic
        context['attributes_static'] = self.attributes_static

        return context

view_classificator_detail = ClassificatorDetailView.as_view()


class ClassificatorChangeView(ClassificatorAttributesMixin, generic.DetailView):
    """Classificators's change view.
    Handle the creation and update of the
    :class:`apps.media_classification.models.Classificator` objects.
    """
    template_name = 'media_classification/classificators/form.html'
    model = Classificator
    context_object_name = 'classificator'

    def __init__(self, **kwargs):
        super(ClassificatorChangeView, self).__init__(**kwargs)
        self.object = None

    def get_context_data(self, **kwargs):
        """
        Update context data with forms generated based on static and dynamic
        attributes of classificator.
        """
        self.object = self.get_object()
        context = super(
            ClassificatorChangeView, self
        ).get_context_data(**kwargs)

        if self.object:
            self.set_attributes_context(self.object)
            context.update({
                'attributes_static': self.attributes_static,
                'attributes_dynamic': self.attributes_dynamic,
            })

        return context

    def get(self, request, *args, **kwargs):
        """Prepare all data required to render form that user will use to build
        own classificator"""
        context = self.get_context_data(**kwargs)

        predefined_form_params = {}
        if self.object:
            predefined_form_params = {
                'initial': self.object.parse_hstore_values('predefined_attrs')
            }

        predefined_form = PredefinedAttributeForm(**predefined_form_params)
        update_attr = kwargs.get('update_custom_attr', None)

        custom_form_params = {}
        if update_attr:
            custom_form_params = {
                'initial': self.object.parse_hstore_values(
                    'custom_attrs', update_attr
                )[update_attr]
            }
            custom_form_params['initial']['name'] = update_attr

        custom_form = CustomAttributeForm(**custom_form_params)

        classificator_form = ClassificatorForm(
            instance=self.object, prefix='classificator'
        )

        context.update({
            'predefined_form': predefined_form,
            'custom_form': custom_form,
            'classificator_form': classificator_form,
        })

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """Classificator can be updated with multiple ways:

        * when 'main' button for adding/updating classificator is used
        * when custom attributes definition is changed

        In this method all changes sent by user are stored in classificator,
        and if classificator is created, currently logged in user is
        assigned as owner.
        """
        context = self.get_context_data(**kwargs)
        classificator_form = ClassificatorForm(
            request.POST, instance=self.object, prefix='classificator'
        )
        custom_form = CustomAttributeForm(request.POST)
        predefined_form = PredefinedAttributeForm(request.POST)

        errors = None
        redirect_to_update = False

        if classificator_form.is_valid():
            instance = classificator_form.save(commit=False)
            if not instance.pk:
                instance.owner = request.user
                redirect_to_update = True

            # Handle predefined attrs alwys on normal submit
            if predefined_form.is_valid():
                instance.set_predefined_attrs(
                    predefined_data=predefined_form.cleaned_data
                )
            else:
                errors = 'The pre-defined attribute form contains errors'

            # Submit for custom attrs has to be clicked to work with
            # setting custom attrs
            if 'custom_attrs_manage' in request.POST:
                if custom_form.is_valid():
                    name = custom_form.cleaned_data.pop('name')

                    instance.set_custom_attr(
                        name=name, params=custom_form.cleaned_data
                    )
                else:
                    errors = u"The custom attribute form contains errors"

            instance.save()
        else:
            errors = 'The classificator form contains errors'
            instance = None

        if errors:
            messages.error(
                request=request,
                message=errors
            )
            context.update({
                'classificator_form': classificator_form,
                'predefined_form': predefined_form,
                'custom_form': custom_form,
            })
            if redirect_to_update:
                return redirect(
                    'media_classification:classificator_update', instance.pk
                )
            return self.render_to_response(context)

        return redirect(
            'media_classification:classificator_update', instance.pk
        )


class ClassificatorCreateView(LoginRequiredMixin, ClassificatorChangeView):
    """Classificators's create view.
    Handle the creation of the
    :class:`apps.media_classification.models.Classificator` objects.
    """
    def get_object(self, queryset=None):
        self.object = None


view_classificator_create = ClassificatorCreateView.as_view()


class ClassificatorCloneView(LoginRequiredMixin, generic.DetailView):
    """Each classificator can be cloned, so user can create own classificator
    but based on some other existing classificator.
    When classificator is cloned, name is changed and all attributes of
    cloned classificator are copied into newly created one.
    """
    model = Classificator

    def post(self, request, *args, **kwargs):
        """Create copy of selected classificator and save it's attributes
        under new name.
        After creation user is redirected to details of new classificator.
        """
        item = self.get_object()
        old_item = self.get_object()

        if old_item.copy_of:
            copy_of = old_item.copy_of
        else:
            copy_of = old_item

        count = Classificator.objects.filter(copy_of=copy_of).count() + 1

        item.pk = None
        item.name = Classificator.CLONE_PATTERN.format(
            count=count,
            name=copy_of.name,
        )
        item.copy_of = copy_of
        item.owner = request.user
        item.save()

        messages.add_message(
            self.request,
            messages.SUCCESS,
            (
                'Old classificator <strong>{old_name}</strong> has been '
                'copied as <strong>{name}</strong>'
            ).format(
                old_name=old_item.name,
                name=item.name
            )
        )
        return redirect(
            'media_classification:classificator_detail', item.pk
        )


view_classificator_clone = ClassificatorCloneView.as_view()


class ClassificatorUpdateView(
    LoginRequiredMixin, UserPassesTestMixin, ClassificatorChangeView
):
    """Classificators's update view.
    Handle the update of the
    :class:`apps.media_classification.models.Classificator` objects.
    """
    raise_exception = True

    def test_func(self, user):
        """Only users that have update permissions can change given
        clasificator"""
        return self.get_object().can_update(user)

    def post(self, request, *args, **kwargs):
        """Update attributes in classifiator using entered user data"""
        self.object = self.get_object()
        if request.POST.get('updateAttr'):
            name = request.POST['updateAttr']
            kwargs['update_custom_attr'] = name
            return self.get(request, *args, **kwargs)

        if request.POST.get('removeAttr'):
            self.object.remove_custom_attr(
                name=request.POST['removeAttr'], commit=True
            )
            return self.get(request, *args, **kwargs)
        return super(
            ClassificatorUpdateView, self
        ).post(request, *args, **kwargs)

view_classificator_update = ClassificatorUpdateView.as_view()


class ClassificatorDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    classificators.

    Only classificators that user has enough permissions for can be deleted
    """

    model = Classificator
    redirect_url = 'media_classification:classificator_list'


view_classificator_delete = ClassificatorDeleteView.as_view()
