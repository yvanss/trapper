# -*- coding: utf-8 -*-
"""
Views used to handle logic related to classification management in media
1classification application
"""
from __future__ import unicode_literals

from functools import partial, wraps

from braces.views import UserPassesTestMixin, JSONResponseMixin
from bulk_update.helper import bulk_update

from django.shortcuts import render, redirect, get_object_or_404
from django.views import generic
from django.conf import settings
from django.contrib import messages
from django.forms.models import formset_factory
from django.core.urlresolvers import reverse
from django.apps import apps
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from trapper.apps.common.tools import datetime_aware
from trapper.apps.media_classification.models import (
    ClassificationProject, Classification, ClassificationDynamicAttrs,
    UserClassification, UserClassificationDynamicAttrs,
    ClassificationProjectCollection
)
from trapper.apps.media_classification.forms import (
    ClassificationForm, ClassifyMultipleForm,
    ClassificationImportForm, ClassificationExportForm
)
from trapper.apps.media_classification.taxonomy import (
    ClassificatorSettings, ClassificationStatus, ClassifyMessages,
    ClassificationProjectRoleLevels
)
from trapper.apps.media_classification.forms import ClassificationTagForm
from trapper.apps.media_classification.tasks import (
    celery_import_classifications, celery_create_tags,
    celery_results_to_data_package
)
from trapper.apps.geomap.models import MapManagerUtils, Deployment
from trapper.apps.common.views import LoginRequiredMixin, BaseDeleteView
from trapper.apps.common.tools import parse_hstore_field, parse_pks
from trapper.apps.accounts.models import UserTask

User = get_user_model()


class ClassifyCollectionView(
    LoginRequiredMixin, UserPassesTestMixin, generic.View
):
    """
    """
    raise_exception = True

    def get_project(self, project_pk):
        """Return classification project for given pk or return HTTP 404"""
        return get_object_or_404(ClassificationProject, pk=project_pk)

    def test_func(self, user):
        """This view can be accessed only if currently logged in user
        can at least view classification project"""
        project_pk = self.kwargs.get('project_pk', None)
        project = self.get_project(project_pk=project_pk)
        return project.can_view(user)

    def get_collection(self, project_pk, collection_pk):
        """Return classification project collection for given pk within given
        classification project or return HTTP 404."""

        return get_object_or_404(
            ClassificationProjectCollection,
            project__pk=project_pk, pk=collection_pk
        )

    def get(self, request, *args, **kwargs):
        """
        """

        project_pk = kwargs['project_pk']
        collection_pk = kwargs['collection_pk']
        collection = self.get_collection(
            project_pk=project_pk,
            collection_pk=collection_pk
        )
        deployments = request.GET.get('deployments', None)
        
        if deployments:
            params = {
                'resource__deployment__pk__in': parse_pks(deployments)
            }
        else:
            params = {}
        classification = collection.classifications.filter(
            **params
        ).order_by('resource__date_recorded').first()

        if not classification:
            messages.error(
                request=self.request,
                message=(
                    'Selected collection contains no resources. '
                    'Nothing to classify.'
                )
            )
            return redirect(
                reverse(
                    'media_classification:project_detail',
                    kwargs={'pk': project_pk}
                )
            )
        url = reverse(
            'media_classification:classify',
            kwargs={
                'pk': classification.pk
            }
        )
        if deployments:
            return redirect(
                '{url}?deployments={deployments_pks}'.format(
                    url = url,
                    deployments_pks = deployments
                )
            )
        else:
            return redirect(url)


view_classify_collection = ClassifyCollectionView.as_view()


class ClassifyResourceView(
    LoginRequiredMixin, UserPassesTestMixin, generic.View
):
    """Classify resources according to defined classifcation forms.
    """

    http_method_names = ['get', 'post']
    raise_exception = True
    readonly = False
    form_template = (
        'media_classification/classifications/classify/forms_{name}.html'
    )
    dynamic_form_template = None

    def test_func(self, user):
        """Only users that have access to a classification project can
        classify resources.
        """

        classification_pk = self.kwargs.get('pk', None)
        self.classification = self.get_classification(classification_pk)
        return self.classification.project.can_view(user)

    def get_classification(self, classification_pk):
        """Return classification for given pk or return HTTP 404."""

        return get_object_or_404(Classification.objects.select_related(
            'project__owner', 'project__classificator', 'resource',
            'resource__deployment'
        ).prefetch_related(
            'user_classifications__owner'
        ), pk=classification_pk)

    def get_dynamic_form(
        self, classificator, fields_defs, user_classification, readonly=False
    ):
        """Build a dynamic formset that will be used for classifications.
        """

        dynamic_form = None

        if fields_defs['D']:
            dynamic_attrs_order = classificator.get_dynamic_attrs_order()
            custom_class_form_initial = []
      
            extra = 0
            if user_classification:
                for data in user_classification.dynamic_attrs.values_list(
                        'attrs', flat=True
                ):
                    custom_class_form_initial.append(
                        parse_hstore_field(data)
                    )
            else:
                extra = 1
                
            # http://stackoverflow.com/questions/622982/
            dynamic_class_formset = formset_factory(
                wraps(ClassificationForm)(
                    partial(
                        ClassificationForm,
                        fields_defs=fields_defs['D'],
                        attrs_order=dynamic_attrs_order,
                        readonly=readonly
                    )
                ),
                extra=extra,
                )
            dynamic_form = dynamic_class_formset(
                data=self.request.POST or None,
                initial=custom_class_form_initial
            )
            # to be used as a template
            self.dynamic_form_template = dynamic_form.empty_form
        return dynamic_form

    def get_static_form(
        self, classificator, fields_defs, user_classification, readonly=False
    ):
        """Build a static form that will be used for classifications.
        """

        static_class_form = None
        if fields_defs['S']:
            static_attrs_order = classificator.get_static_attrs_order()
            predefined_class_form_initial = None
            if user_classification and user_classification.static_attrs:
                predefined_class_form_initial = parse_hstore_field(
                    user_classification.static_attrs
                )

            static_class_form = ClassificationForm(
                data=self.request.POST or None,
                fields_defs=fields_defs['S'],
                attrs_order=static_attrs_order,
                initial=predefined_class_form_initial,
                readonly=readonly
            )
        return static_class_form

    def get_form_template(self, classificator):
        """Classificator can use different templates that are used
        to render classification forms; here we can determine which 
        template should be used"""

        template = None
        if classificator is not None:
            template = self.form_template.format(name=classificator.template)
        return template

    def get_user(self):
        user_pk = self.kwargs.get('user_pk', None)
        user = None
        if user_pk:
            try:
                user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                messages.warning(
                    request=self.request,
                    message=(
                        'We are sorry but requested user does not exist.'
                    )
                )
        if not user:
            user = self.request.user
        return user

    def is_readonly(self, is_project_admin):
        """Determine if form should be readonly or not"""
        return self.readonly and not is_project_admin

    def redirect_to_approved(self, user):
        if (
                self.classification.approved_source and not
                self.classification.approved_source.owner == user
        ):
            redirect_obj = redirect(
                reverse(
                    'media_classification:classification_detail',
                kwargs={
                    'pk': self.classification.approved_source.pk,
                })
            )
            return (True, redirect_obj)
        return (False, '')

    def get(self, request, *args, **kwargs):
        """
        """

        user = self.get_user()
        current_user = request.user
        user_classifications = self.classification.user_classifications.all()
        request_user_classification = [
            k for k in user_classifications if k.owner == current_user
        ]
        user_classification = [k for k in user_classifications if k.owner == user]
        if user_classification:
            user_classification = user_classification[0]
        else:
            user_classification = None

        if not user_classification:
            redirect_bool, redirect_obj = self.redirect_to_approved(user)
            if redirect_bool and not self.request.GET.get('add_my_classification'):
                return redirect_obj
        static_form = None
        dynamic_form = None
        multiple_classify_form = None

        collection = self.classification.collection
        project = self.classification.project
        is_project_admin = project.is_project_admin(user=current_user)
        is_readonly = self.is_readonly(is_project_admin=is_project_admin)

        storage_collection = collection.collection.collection
        resource = self.classification.resource
        deployments = storage_collection.resources.values_list(
            'deployment__pk',
            'deployment__deployment_id'
        ).order_by('deployment__deployment_id').distinct()

        show_forms = True

        classificator = project.classificator
        if not classificator:
            messages.warning(
                request=self.request,
                message=ClassifyMessages.MSG_CLASSIFICATOR_MISSING
            )

        show_forms = show_forms and classificator

        if show_forms:
            fields_defs = classificator.prepare_form_fields()
            dynamic_form = self.get_dynamic_form(
                classificator=classificator,
                fields_defs=fields_defs,
                user_classification=user_classification,
                readonly=is_readonly
            )
            static_form = self.get_static_form(
                classificator=classificator,
                fields_defs=fields_defs,
                user_classification=user_classification,
                readonly=is_readonly
            )
            multiple_classify_form = ClassifyMultipleForm(
                initial={'collection': collection.pk}
            )

        context = {
            'project': project,
            'collection': collection,
            'storage_collection': storage_collection,
            'resource': resource,
            'deployments': deployments,
            'user_classifications': user_classifications,
            'static_form': static_form,
            'dynamic_form': dynamic_form,
            'dynamic_form_template': self.dynamic_form_template,
            'classification': self.classification,
            'user_classification': user_classification,
            'request_user_classification': request_user_classification,
            'is_project_admin': is_project_admin,
            'is_readonly': is_readonly,
            'form_template': self.get_form_template(
                classificator=classificator
            ),
            'multiple_classify_form': multiple_classify_form,
        }

        return render(
            request,
            'media_classification/classifications/classify/index.html',
            context
        )

    def post(self, request, *args, **kwargs):
        """When a user has enough permissions and filled all neccessery
        fields in classification forms then this method is used to save all 
        provided data to a database object
        :class:apps.media_classification.models.UserClassification`.

        If a currently logged in user is a Project Admin and decide that
        this classification should be approved, then after user classification
        is saved, :class:apps.media_classification.models.Classification`
        object is updated with current classification data and classification
        is marked as approved.
        """

        user = self.get_user()
        now = datetime_aware()

        collection = self.classification.collection
        project = self.classification.project
        base_resource = self.classification.resource

        # If there is no classificator, there is no reason to go further
        classificator = project.classificator
        if not classificator:
            messages.error(
                request=request,
                message=ClassifyMessages.MSG_CLASSIFICATOR_MISSING
            )
            return self.get(request, *args, **kwargs)

        is_project_admin = project.is_project_admin(request.user)

        # Update classification other user is avaiilable for project admin
        if user != request.user and not is_project_admin:
            messages.error(
                request=request, message=ClassifyMessages.MSG_PERMS_REQUIRED
            )
            return self.get(request, *args, **kwargs)

        # If user is not project admin and tries to approve it... Don't let it
        if not is_project_admin and 'approve_classification' in request.POST:
            messages.error(
                request=request, message=ClassifyMessages.MSG_PERMS_REQUIRED
            )
            return self.get(request, *args, **kwargs)

        # seems like all base stuff is ok, we can prepare some stuff
        resources = {base_resource}

        if (
                'classify_multiple' in request.POST or
                'approve_multiple' in request.POST
        ):
            multiple_classify_form = ClassifyMultipleForm(
                request.POST, initial={
                    'collection': collection,

                    }
                )
            if multiple_classify_form.is_valid():
                cleaned_data = multiple_classify_form.cleaned_data
                resources.update(cleaned_data['selected_resources'])
            else:
                messages.error(
                    request=request,
                    message=ClassifyMessages.MSG_CLASSIFY_MULTIPLE_FAILED
                )
                return self.get(request, *args, **kwargs)

        # finally we got there... we can work with resource(s)!
        fields_defs = classificator.prepare_form_fields()

        errors = False
        for resource in resources:
            classification, created = Classification.objects.get_or_create(
                resource=resource,
                collection=collection,
                project=project,
                defaults={
                    'created_at': now,
                    'owner': user,
                    'status': ClassificationStatus.REJECTED,
                    'updated_at': now,
                    'updated_by': user
                }
            )

            if not created:
                classification.updated_at = now
                classification.updated_by = user
                classification.save()

            user_classification, created = \
                UserClassification.objects.get_or_create(
                    classification=classification,
                    owner=user,
                    defaults={
                        'created_at': now,
                        'updated_at': now,
                        }
                )

            if not created:
                user_classification.updated_at = now

            dynamic_form = self.get_dynamic_form(
                classificator=classificator,
                fields_defs=fields_defs,
                user_classification=user_classification,
            )
            static_form = self.get_static_form(
                classificator=classificator,
                fields_defs=fields_defs,
                user_classification=user_classification,
            )

            if (
                static_form and not static_form.is_valid() or
                dynamic_form and not dynamic_form.is_valid()
            ):
                messages.error(
                    request=request,
                    message=ClassifyMessages.MSG_CLASSIFY_ERRORS
                )
                return self.get(
                    request, 
                    *args, **kwargs
                )
                            
            # process data POST'ed by static form
            if static_form:
                user_classification.static_attrs = static_form.cleaned_data

            # Now we should have all required data, so we can save
            user_classification.save()

            if dynamic_form:
                # bulk-delete of old rows
                user_classification.dynamic_attrs.all().delete()

                # populate new ones
                for form in dynamic_form.forms:
                    attrs = UserClassificationDynamicAttrs.objects.create(
                        userclassification=user_classification,
                        attrs=form.cleaned_data
                    )
            # If processed resource is currently classified one, then
            # check if it shouldn't be approved
            if (
                (
                    resource == base_resource and
                    'approve_classification' in request.POST
                ) or (
                    'approve_multiple' in request.POST
                )
            ):
                if classification.project.is_project_admin(user=user):
                    classification.status = True
                    classification.approved_by = user
                    classification.approved_at = datetime_aware()
                    classification.approved_source = user_classification

                    if static_form:
                        classification.static_attrs = static_form.cleaned_data
                    classification.save()

                    classification.dynamic_attrs.all().delete()
                    for attr in user_classification.dynamic_attrs.all():
                        user_attrs = attr.attrs
                        ClassificationDynamicAttrs.objects.create(
                            classification=classification,
                            attrs=user_attrs
                        )
                else:
                    messages.error(
                        request=request,
                        message=ClassifyMessages.MSG_APPROVE_PERMS
                    )
                    return self.get(
                        request, 
                        *args, **kwargs
                    )

        messages.success(
            request=request,
            message=ClassifyMessages.MSG_SUCCESS
        )
        return redirect(
            reverse(
                'media_classification:classify_user',
                kwargs={
                    'pk': classification.pk,
                    'user_pk': user.pk
                })
        )


view_classify_resource = ClassifyResourceView.as_view()


class ClassificationDetailView(ClassifyResourceView):
    """
    """

    readonly = True
    http_method_names = ['get']

    def test_func(self, user):
        """Only users that have access to a classification project can
        view classification details."""

        user_classification = self.get_user_classification()
        self.classification = self.get_classification(
            user_classification.classification.pk
        )
        self.user = user_classification.owner
        return self.classification.project.can_view(user)

    def is_readonly(self, is_project_admin):
        return True

    def get_user_classification(self):
        user_classification = get_object_or_404(
            UserClassification, pk=self.kwargs['pk']
        )
        return user_classification

    def get_user(self):
        return self.user

    def redirect_to_approved(self, *args, **kwargs):
        return (False,'')


view_classification_detail = ClassificationDetailView.as_view()


class ClassificationGridContextMixin(object):
    """
    """

    def get_classification_url(self, **kwargs):
        return reverse('media_classification:api-classification-list')

    def get_classification_context(self, **kwargs):
        project = kwargs.get('project', None)
        is_admin = project.is_project_admin(self.request.user)
        context = {
            'data_url': self.get_classification_url(**kwargs),
            'maps': MapManagerUtils.get_accessible(user=self.request.user),
            'project': project,
            'model_name': 'classifications',
            'update_redirect': 'true',
            'hide_delete': not is_admin,
            'is_admin': is_admin
        }

        if project:

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


class ClassificationListView(
    LoginRequiredMixin, UserPassesTestMixin, generic.ListView,
    ClassificationGridContextMixin
):
    """List view of
    :class:`apps.media_classification.models.Classification` instances.
    This list is always limited to a given classification project.
    """

    template_name = 'media_classification/classifications/list.html'
    raise_exception = True

    def get_classification_url(self, **kwargs):
        """Alter url for classification DRF API, to get only classifications
        that belong to given classification project"""
        project_pk = self.kwargs['pk']
        return '{url}?project={pk}'.format(
            url=reverse('media_classification:api-classification-list'),
            pk=project_pk
        )

    def get_project(self):
        """Return classification project for given pk or return HTTP 404"""
        return get_object_or_404(ClassificationProject, pk=self.kwargs['pk'])

    def test_func(self, user):
        """Check if user has enough permissions to view classifications"""
        return self.get_project().can_view_classifications(user)

    def build_filters(self):
        """
        """
        filter_definition = []
        project = self.get_project()

        classificator = project.classificator
        if not classificator:
            messages.warning(
                request=self.request,
                message=(
                    'This project has no classificator assigned.'
                )
            )
            return filter_definition

        predefined_def = classificator.parse_hstore_values('predefined_attrs')
        custom_def = classificator.parse_hstore_values('custom_attrs')

        static_attrs_list = classificator.static_attrs_order

        for name, params in custom_def.items():
            if name in static_attrs_list:
                field_type = 'static_attrs'
            else:
                field_type = 'dynamic_attrs'

            field = {
                'label': name.capitalize(),
                'name': name,
                'field': field_type,
            }
            if params['field_type'] == ClassificatorSettings.FIELD_BOOLEAN:
                field['tag'] = {
                    'name': 'select', 'is_block': True
                }
                field['values'] = [
                    ('All', ''),
                    ('True', 'true'),
                    ('False', 'false')
                ]
            elif params['values']:
                values = params['values'].split(',')
                if settings.EXCLUDE_CLASSIFICATION_NUMBERS:
                    tmp_vals = []
                    for val in values:
                        try:
                            float(val)
                        except ValueError:
                            # If this is not number, add it to list
                            tmp_vals.append(val)
                    values = tmp_vals

                if values:
                    field['tag'] = {'name': 'select', 'is_block': True}
                    field['values'] = [('All', '')] + zip(values, values)
                else:
                    field['tag'] = {'name': 'input', 'is_block': False}

            else:
                field['tag'] = {'name': 'input', 'is_block': False}

            if field['tag']['name'] != 'input':
                filter_definition.append(field)

        # work with predefined attrs
        model_attributes = ClassificatorSettings.PREDEFINED_ATTRIBUTES_MODELS

        for name, params in model_attributes.items():
            if name in static_attrs_list:
                field_type = 'static_attrs'
            else:
                field_type = 'dynamic_attrs'

            if predefined_def.get(name, False):
                values = predefined_def.get(
                    'selected_{name}'.format(name=name), None
                )
                model_class = apps.get_model(params['app'], name)
                dbvalues = [('All', '')] + list(
                    model_class.objects.filter(
                        pk__in=values
                    ).values_list(
                        params['choices_labels'],
                        params['choices_labels']
                    )
                )

                field = {
                    'label': name.capitalize(),
                    'name': name,
                    'field': field_type,
                    'tag': {'name': 'select', 'is_block': True},
                    'values': dbvalues
                }
                filter_definition.append(field)

        if predefined_def.get('annotations', False):
            # Annotation filter should not be displayed on classification list
            pass
        if predefined_def.get('comments', False):
            # Comments should not be listed as field
            pass

        filter_definition.sort(key=lambda x: x['label'])
        return filter_definition

    def get_context_data(self, **kwargs):
        """Update context used to render template with classification context
        and filters"""

        project = self.get_project()
        context = {
            'classification_context': self.get_classification_context(
                project=project
            ),
        }
        context['classification_context']['filters'] = self.build_filters()
        context['classification_context']['update_redirect'] = False

        return context

    def get_queryset(self):
        pass


view_classification_list = ClassificationListView.as_view()


class ClassificationDeleteView(BaseDeleteView):
    """
    """

    model = Classification
    redirect_url = 'media_classification:classification_list'

    def add_message(self, status, template, item):
        """Classification has no `name` attribute so we have
        to overwrite this method"""
        messages.add_message(self.request, status, template)

    def get_classification(self):
        """Get classification for given pk"""
        return Classification.objects.get(
            pk=self.kwargs['pk']
        )

    def test_func(self, user):
        """Verify that user is project admin of project that contain
        deleted classification before removal"""
        return self.get_classification().project.is_project_admin(user=user)

    def get_redirect_url(self):
        """
        Redirect to classification list after classification is removed if
        possible or to project list"""
        classification = getattr(self, '_item_copy', None)

        if classification:
            url = reverse(self.redirect_url, args=[classification.project.pk])
        else:
            url = reverse('media_classification:project_index')
        return redirect(url)

    def delete_item(self, item):
        item.delete(clear=True)

    def bulk_delete(self, queryset):
        """Instead of deleting classification objects bulk clear
        their attributes
        """
        to_update = []
        pks = []
        for obj in queryset:
            obj.static_attrs = {}
            obj.status = False
            obj.approved_by = None
            obj.approved_at = None
            obj.approved_source_id = None
            obj.updated_at = now()
            obj.updated_by = self.request.user
            to_update.append(obj)
            pks.append(obj.pk)
        bulk_update(to_update, update_fields=[
            'static_attrs', 'status', 'approved_by',
            'approved_at', 'approved_source_id',
            'updated_at', 'updated_by'
        ])
        ClassificationDynamicAttrs.objects.filter(
            classification__pk__in=pks
        ).delete()

    def filter_editable(self, queryset, user):
        return self.model.objects.get_accessible(
            user=user,
            base_queryset=queryset,
            role_levels=[
                ClassificationProjectRoleLevels.ADMIN,
            ]
        )


view_classification_delete = ClassificationDeleteView.as_view()


class ClassificationTagView(
    LoginRequiredMixin, generic.DetailView, JSONResponseMixin
):
    """
    """
    template_name = 'media_classification/classifications/form_tag.html'
    context_object_name = 'project'
    model = ClassificationProject

    EXCLUDE_VALS = [
        '[]', None, '', 'False', 'True', False, True, 'false', 'true'
    ]
    INCLUDE_CUSTOM_FIELDS = ['S',] # 'S' - string
    INCLUDE_PREDEFINED_FIELDS = ['species',]

    def get_context_data(self, **kwargs):
        if not self.object.classificator:
            msg = 'This classification project does not have the classificator. \
            It is impossible to build tags definitions'
            return self.render_json_response({
                'status': False,
                'msg': msg,
            })
        context = super(ClassificationTagView, self).get_context_data(**kwargs)
        form_data = self.get_form_data()
        context['form'] = ClassificationTagForm(form_data=form_data)
        return context

    def get_form_data(self):
        tag_keys = []
        tag_keys.extend(self.INCLUDE_PREDEFINED_FIELDS)
        classificator = self.object.classificator
        custom_attrs = classificator.parse_hstore_values('custom_attrs')
        for field in custom_attrs.keys():
            if custom_attrs[field]['field_type'] in self.INCLUDE_CUSTOM_FIELDS:
                tag_keys.append(field)
        return tag_keys

    def post(self, request, *args, **kwargs):
        """
        """
        user = self.request.user
        status = False
        msg = 'No resources to update or you have no permission \
        to update selected resources.'
        data = request.POST.copy()
        if 'classifications_pks' in data:

            classifications_pks = data['classifications_pks'] or ''
            del data['classifications_pks']
            classifications_pks = parse_pks(classifications_pks)
            classifications = Classification.objects.filter(
                Q(resource__owner=user) | Q(resource__managers=user)
            ).filter(
                pk__in=classifications_pks
            ).select_related(
                'resource'
            )

            tag_keys = data.keys()

            if classifications:

                params = {
                    'data': {
                        'classifications': list(classifications),
                        'tag_keys': tag_keys
                    },
                    'user': user
                }
                if settings.CELERY_ENABLED:
                    task = celery_create_tags.delay(**params)
                    user_task = UserTask(
                        user=user,
                        task_id=task.task_id
                    )
                    user_task.save()
                    msg = (
                        'You have successfully run a celery task. Tags for  '
                        'selected resources are being created now.'
                    )
                else:
                    msg = celery_create_tags(**params)
                status = True

        return self.render_json_response({
            'status': status,
            'msg': msg,
        })


view_classification_tag = ClassificationTagView.as_view()


class ClassifyApproveView(LoginRequiredMixin, generic.View):
    """
    """

    model = Classification

    def post(self, request, *args, **kwargs):
        """
        """

        error_redirect = redirect(
            request.META.get('HTTP_REFERER') or
            reverse('media_classification:project_index')
        )
        user = request.user

        try:
            user_classification = UserClassification.objects.get(
                pk=kwargs['pk']
            )
        except UserClassification.DoesNotExist:
            messages.error(
                request=request,
                message=ClassifyMessages.MSG_CLASSIFICATION_MISSING
            )
            return error_redirect

        classification = user_classification.classification

        if not classification.can_approve(user=user):
            messages.error(
                request=request,
                message=ClassifyMessages.MSG_APPROVE_PERMS
            )
            return error_redirect

        classification.status = True
        classification.approved_by = user
        classification.approved_at = datetime_aware()
        classification.approved_source = user_classification
        classification.static_attrs = user_classification.static_attrs
        classification.save()

        classification.dynamic_attrs.all().delete()
        for dynamic_attr in user_classification.dynamic_attrs.all():
            user_attrs = dynamic_attr.attrs
            ClassificationDynamicAttrs.objects.create(
                classification=classification,
                attrs=user_attrs
            )
        messages.success(
            request=request,
            message=ClassifyMessages.MSG_SUCCESS_APPROVED
        )
        return redirect(
            reverse(
                'media_classification:classify',
                kwargs={
                    'pk': classification.pk,
                })
        )

view_classify_approve = ClassifyApproveView.as_view()


class ClassificationImportView(LoginRequiredMixin, generic.FormView):

    """Imports classifications from csv tables.
    """

    template_name = 'media_classification/classifications/classification_import.html'
    form_class = ClassificationImportForm
    success_url = None

    def get_form(self, form_class=None):
        form = super(ClassificationImportView, self).get_form(form_class)
        project_pk = self.kwargs.get('pk')
        if project_pk:
            try:
                project = ClassificationProject.objects.get(pk=project_pk)
            except ClassificationProject.DoesNotExist:
                raise
            form.fields['project'].initial = project
        return form

    def form_valid(self, form):
        """The form is valid so create/update classification objects.
        """
        user = self.request.user
        project = form.cleaned_data.get('project')

        if not project.is_project_admin(user=user):
            messages.error(
                request=self.request,
                message=(
                    'You are not allowed to import classifications'
                    'into selected project. Admin role is required for that.'
                )
            )
            self.success_url = '.'
        else:
            params = {
                'data': form.cleaned_data,
                'user': user,
            }
            if settings.CELERY_ENABLED:
                task = celery_import_classifications.delay(**params)
                user_task = UserTask(
                    user=user,
                    task_id=task.task_id
                )
                user_task.save()
                msg = (
                    'You have successfully run a celery task. Classifications '
                    'are being imported now.'
                )
            else:
                msg = celery_import_classifications(**params)

            messages.success(
                request=self.request,
                message=msg
            )
            self.success_url = reverse(
                'accounts:dashboard'
            )
        return super(ClassificationImportView, self).form_valid(form)


view_classification_import = ClassificationImportView.as_view()


class ClassificationExportView(LoginRequiredMixin, generic.FormView):

    """This view exports classifications into csv files, optionally it generates
    additional table with data on deployments. It can also generate
    EML (Ecological Metadata Language) file which describes a whole dataset.
    """

    template_name = 'media_classification/classifications/classification_export.html'
    form_class = ClassificationExportForm
    success_url = None

    def get_form(self, form_class=None):
        form = super(ClassificationExportView, self).get_form(form_class)
        project_pk = self.kwargs.get('pk')
        try:
            project = ClassificationProject.objects.get(
                pk=project_pk
            )
        except ClassificationProject.DoesNotExist:
            raise
        self.project = project
        return form

    def form_valid(self, form):
        """Export classifications
        """
        user = self.request.user

        if not self.project.is_project_admin(user=user):
            messages.error(
                request=self.request,
                message=(
                    'You are not allowed to export classifications'
                    'from this project. The admin role is required for that.'
                )
            )
            self.success_url = '.'

        elif not self.project.classificator:
            messages.error(
                request=self.request,
                message=(
                    'There is no classificator assigned to this project.'
                )
            )
            self.success_url = '.'

        else:
            params = {
                'data': form.cleaned_data,
                'user': user,
                'project': self.project
            }

            if settings.CELERY_ENABLED:
                task = celery_results_to_data_package.delay(**params)
                user_task = UserTask(
                    user=user,
                    task_id=task.task_id
                )
                user_task.save()
                msg = (
                    'You have successfully run a celery task. The requested data package '
                    'is being generated now.'
                )
            else:
                msg = celery_results_to_data_package(**params)

            messages.success(
                request=self.request,
                message=msg
            )
            self.success_url = reverse(
                'media_classification:project_detail',
                kwargs={'pk': self.project.pk}
            )
        return super(ClassificationExportView, self).form_valid(form)


view_classification_export = ClassificationExportView.as_view()
