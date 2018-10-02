# -*- coding: utf-8 -*-
"""
Views used to handle logic related to sequence management in media
classification application
"""
from __future__ import unicode_literals

from django.views import generic
from django.core.exceptions import ValidationError
from django.conf import settings
from django.template import RequestContext
from django.template.loader import render_to_string

from braces.views import JSONResponseMixin

from trapper.apps.media_classification.models import (
    Classification, ClassificationProjectCollection,
    Sequence, SequenceResourceM2M
)
from trapper.apps.accounts.models import UserTask
from trapper.apps.common.views import BaseDeleteView, LoginRequiredMixin
from trapper.apps.common.tools import parse_pks, datetime_aware
from trapper.apps.storage.models import Resource
from trapper.apps.media_classification.serializers import (
    SequenceReadSerializer
)
from trapper.apps.media_classification.forms import SequenceBuildForm
from trapper.apps.media_classification.tasks import celery_build_sequences


class SequenceChangeView(LoginRequiredMixin, generic.View, JSONResponseMixin):
    """
    Sequence's create or update view.
    Handle the creation or update of the
    :class:`apps.media_classification.models.Sequence` objects.

    Sequence modifications can be done only using POST method, and response
    is given as json
    """

    http_method_names = ['post']
    raise_exception = True
    redirect_url = None

    def raise_exception_handler(self, request, *args, **kwargs):
        """For ajax requests if user is not authenticated, instead of
        redirection or access denied page, json with proper message is
        created"""
        context = {'status': False, 'msg': 'Authentication required'}
        return self.render_json_response(context)

    def get_collection(self, collection_pk):
        """For given collection pk return
        :class:`apps.media_classification.model.ClassificationProjectCollection`
        instance if such exists"""
        try:
            collection = ClassificationProjectCollection.objects.get(
                pk=collection_pk
            )
        except ClassificationProjectCollection.DoesNotExist:
            collection = None
        return collection

    def get_resources(self, collection, resource_pks):
        """For given collection and resource pk return
        :class:`apps.storage.model.Resource` objects but only those
        that are accessible for currently logged in user"""
        base_queryset = collection.collection.collection.resources.filter(
            pk__in=parse_pks(resource_pks)
        )
        return Resource.objects.get_accessible(
            base_queryset=base_queryset,
            user=self.request.user,
            basic=True
        )

    def post(self, request, *args, **kwargs):
        """
        `request.POST` method is used to create sequences for given
        list of resources using AJAX.

        List of project pks is passed in `pks` key as list of integers
        separated by comma.

        Sequence can be created for multiple resources that belong to the
        same classification project collection within classification project.

        Response contains status of creation/update and serialized sequence
        object.
        """
        msg = 'Invalid request'
        status = False
        record = None
        collection = None
        sequence_original = None

        collection_pk = request.POST.get('collection_pk') or None
        resources = request.POST.get('resources') or None

        sequence_pk = request.POST.get('pk') or None

        if collection_pk and resources:
            collection = self.get_collection(
                collection_pk=collection_pk
            )
            if collection:
                resources = self.get_resources(
                    collection=collection,
                    resource_pks=resources
                )
        if collection:
            project = collection.project
            if project.can_change_sequence(user=request.user):
                if resources:
                    description = request.POST.get('description', None)

                    try:
                        sequence = Sequence.objects.get(pk=sequence_pk)
                        sequence_original = sequence

                    except Sequence.DoesNotExist:
                        sequence = Sequence(
                            collection=collection,
                            created_by=request.user,
                            created_at=datetime_aware(),
                            description=description,
                        )
                    else:
                        sequence.description = description
                    sequence.save()

                    try:
                        seq_resources = []
                        for resource in resources:
                            obj = SequenceResourceM2M(
                                sequence=sequence,
                                resource=resource
                            )
                            obj.full_clean()
                            seq_resources.append(obj)
                    except ValidationError, e:
                        if sequence_original:
                            sequence = sequence_original
                            sequence.save()
                        else:
                            sequence.delete()
                        msg = e.messages[0]
                    else:
                        sequence.resources.clear()
                        for obj in seq_resources:
                            obj.save()
                        record = SequenceReadSerializer(
                            instance=sequence,
                            context={'request': self.request}
                        ).data
                        status = True
                        # update classification objects with
                        # sequence data
                        sequence.classifications.clear()
                        classifications = Classification.objects.filter(
                            collection=collection,
                            resource__in=resources
                        )
                        classifications.update(sequence=sequence)
            else:
                msg = 'You have not enough permissions to change sequence'

        context = {'status': status, 'record': record, 'msg': msg}
        return self.render_json_response(context)


view_sequence_change = SequenceChangeView.as_view()


class SequenceDeleteView(BaseDeleteView):
    """
    View responsible for handling deletion of single or multiple
    sequences. Only sequences that user has enough permissions for 
    can be deleted.
    """

    model = Sequence
    item_name_field = 'sequence_id'
    redirect_url = 'media_classification:project_list'

    def filter_editable(self, queryset, user):
        to_delete = []
        for obj in queryset:
            if obj.can_delete(user):
                to_delete.append(obj)
        return to_delete

    def bulk_delete(self, queryset):
        for obj in queryset:
            obj.delete()


view_sequence_delete = SequenceDeleteView.as_view()


class SequenceBuildView(
    LoginRequiredMixin, generic.FormView, JSONResponseMixin
):
    """Sequences's (re)build view. Use this view to automatically build
    sequences for specified classification project collections.
    """
    template_name = 'media_classification/projects/sequence_build_form.html'
    form_class = SequenceBuildForm
    raise_exception = True

    def raise_exception_handler(self, request, *args, **kwargs):
        """For ajax requests if user is not authenticated, instead of
        redirection or access denied page, json with proper message is
        created"""
        context = {'success': False, 'msg': 'Authentication required'}
        return self.render_json_response(context)

    def form_valid(self, form):
        """
        """
        if not form.cleaned_data['project_collections']:
            msg = (
                'Nothing to process (most probably you have no permission '
                'to run this action on selected classification project collections)'
            )
            context = {
                'success': False,
                'msg': msg,
            }
        else:
            user = self.request.user
            params = {
                'data': form.cleaned_data,
                'user': user,
            }
            if settings.CELERY_ENABLED:
                task = celery_build_sequences.delay(**params)
                user_task = UserTask(
                    user=user,
                    task_id=task.task_id
                )
                user_task.save()
                msg = (
                    'You have successfully run a celery task. Selected classification '
                    'project collections are being processed now.'
                )
            else:
                msg = celery_build_sequences(**params)
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


view_sequence_build = SequenceBuildView.as_view()
