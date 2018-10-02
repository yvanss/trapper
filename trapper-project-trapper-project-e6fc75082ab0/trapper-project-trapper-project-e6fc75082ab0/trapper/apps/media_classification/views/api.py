# -*- coding: utf-8 -*-
"""Views used by DRF to display json data used by media classification
application"""
from __future__ import unicode_literals

import json
import pandas
import numpy as np
import StringIO

from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.serializers import ValidationError as rest_verror

from bulk_update.helper import bulk_update

from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from trapper.apps.media_classification.models import (
    UserClassification, ClassificationProject, Classificator,
    ClassificationProjectCollection, Classification, Sequence,
    ClassificationDynamicAttrs, UserClassificationDynamicAttrs
)
from trapper.apps.media_classification.filters import (
    UserClassificationFilter, ClassificationProjectFilter,
    ClassificationProjectCollectionFilter, ClassificationFilter,
    SequenceFilter, ClassificatorFilter,
)
from trapper.apps.media_classification.forms import ClassificationForm
from trapper.apps.storage.models import Resource
from trapper.apps.geomap.models import Deployment

from trapper.apps.media_classification import (
    serializers as classification_serializers
)
from trapper.apps.common.views_api import (
    PaginatedReadOnlyModelViewSet, PlainTextRenderer
)
from trapper.apps.common.tools import df_to_geojson, aggregate_results



class UserClassificationViewSet(PaginatedReadOnlyModelViewSet):
    """Returns a list of user classifications."""
    permission_classes = (permissions.IsAuthenticated, )
    queryset = UserClassification.objects.all()
    filter_class = UserClassificationFilter
    serializer_class = classification_serializers.UserClassificationSerializer
    search_fields = [
        'owner__username', 'classification__resource__name',
        '=dynamic_attrs__attrs', '=static_attrs'
    ]
    prefetch_related = [
        'owner__userprofile',
        'dynamic_attrs',
        'classification__resource__deployment__location',
        'classification__collection',
        'classification__project__owner',
    ]

    def get_queryset(self):
        queryset = UserClassification.objects.get_accessible(
            user=self.request.user
        ).prefetch_related(
            *self.prefetch_related
        )
        return queryset


class ClassificationViewSet(PaginatedReadOnlyModelViewSet):
    """Returns a list of classifications.
    """
    permission_classes = (permissions.IsAuthenticated, )
    filter_class = ClassificationFilter
    serializer_class = classification_serializers.ClassificationSerializer
    search_fields = ['resource__name', '=dynamic_attrs__attrs', '=static_attrs']
    prefetch_related = [
        'resource__deployment__location', 'resource__managers',
        'dynamic_attrs',
    ]

    def get_queryset(self):
        queryset = Classification.objects.get_accessible(
            user=self.request.user
        ).prefetch_related(
            *self.prefetch_related
        )
        return queryset


# helper function
def prepare_results_table(queryset, outpath, classificator, return_df=False):
    fields = [
        'static_attrs',
        'dynamic_attrs__attrs', 
        'sequence__sequence_id',
        'resource__deployment__deployment_id',
        'resource__date_recorded',
        'resource__name', 
        'resource__resource_type', 
        'resource_id',
        'id'
    ]
    values = list(queryset.values(*fields))
    static_attrs_columns = classificator.get_static_attrs_order()
    dynamic_attrs_columns = classificator.get_dynamic_attrs_order()
    columns_order = [
        'id', 'resource_id', 'resource__deployment__deployment_id', 'resource__name', 
        'resource__resource_type', 'resource__date_recorded', 'sequence__sequence_id', 
    ] + static_attrs_columns + dynamic_attrs_columns

    for k in values:
        if k.get('static_attrs'):
            k.update(k.pop('static_attrs'))
        else:
            k.pop('static_attrs')
        if k.get('dynamic_attrs__attrs'):
            k.update(k.pop('dynamic_attrs__attrs'))
        else:
            k.pop('dynamic_attrs__attrs')

    df = pandas.DataFrame.from_records(values, columns=columns_order)
    df.columns = [k.split('__')[-1] for k in df.columns]
    df = df.sort(['deployment_id', 'name'])
    df.to_csv(outpath, encoding='utf-8', index=False)
    if return_df:
        return df


class ClassificationResultsView(ListAPIView):
    """Returns a table with classification results.
    """
    permission_classes = (permissions.IsAuthenticated, )
    filter_class = ClassificationFilter
    search_fields = ['resource__name', '=dynamic_attrs__attrs', '=static_attrs']
    prefetch_related = [
        'resource__deployment__location',
        'dynamic_attrs', 'sequence'
    ]
    renderer_classes = (PlainTextRenderer, )

    def get_serializer_class(self):
        pass

    def get_project(self):
        project_pk = self.kwargs.get('project_pk')
        try:
            self.project = ClassificationProject.objects.get(pk=project_pk)
        except ClassificationProject.DoesNotExist:
            self.project = None
        # workaround
        self.request.query_params._mutable = True
        self.request.query_params['project'] = getattr(self.project, 'pk', None)
        self.request.query_params._mutable = False
            
    def get_queryset(self):
        self.get_project()
        queryset = Classification.objects.get_accessible(
            user=self.request.user
        ).prefetch_related(
            *self.prefetch_related
        ).filter(
            project=self.project
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = StringIO.StringIO()
        if self.project:
            classificator = self.project.classificator
            if classificator:
                prepare_results_table(queryset, data, classificator)
        return Response(data.getvalue())


class ClassificationResultsAggView(ListAPIView):
    """Returns a geojson with aggregated classification results.
    """
    permission_classes = (permissions.IsAuthenticated, )
    filter_class = ClassificationFilter
    search_fields = ['resource__name', '=dynamic_attrs__attrs', '=static_attrs']
    prefetch_related = [
        'resource__deployment__location',
        'dynamic_attrs', 'sequence'
    ]
    renderer_classes = (PlainTextRenderer, )
    agg_functions = {
        1: np.sum,
        2: np.min,
        3: np.max,
        4: np.mean
    }
    req_true_str = ('True','true','1','T','t')

    def get_serializer_class(self):
        pass

    def get_extra_params(self):
        p = {
            'by_seq': self.request.query_params.get('seq', False) in self.req_true_str,
            'by_loc': self.request.query_params.get('loc', False) in self.req_true_str,
            'seq_fun': self.request.query_params.get('sfun', 3),
            'count_fun': self.request.query_params.get('cfun', 1),
            'count_var': self.request.query_params.get('cvar', None),
            'all_dep': self.request.query_params.get('adep', False) in self.req_true_str,
            'merge_how': self.request.query_params.get('mhow', 'left'),
            'geojson': self.request.query_params.get('geo', False) in self.req_true_str,
        }
        if not p['seq_fun'] in self.agg_functions.keys():
            raise rest_verror('seq_fun: wrong value')
        if not p['count_fun'] in self.agg_functions.keys():
            raise rest_verror('count_fun: wrong value')
        c = self.project.classificator
        attrs = ','.join(
            [c.dynamic_attrs_order,c.static_attrs_order]
        ).split(',')
        if not str(p['count_var']) in attrs:
            raise rest_verror('count_var: wrong value')
        p['seq_fun'] = self.agg_functions[int(p['seq_fun'])]
        p['count_fun'] = self.agg_functions[int(p['count_fun'])]
        return p

    def get_project(self):
        project_pk = self.kwargs.get('project_pk')
        try:
            self.project = ClassificationProject.objects.get(pk=project_pk)
        except ClassificationProject.DoesNotExist:
            self.project = None
        # workaround
        self.request.query_params._mutable = True
        self.request.query_params['project'] = getattr(self.project, 'pk', None)
        self.request.query_params._mutable = False

    def get_queryset(self):
        self.get_project()
        queryset = Classification.objects.get_accessible(
            user=self.request.user
        ).prefetch_related(
            *self.prefetch_related
        ).filter(
            project=self.project
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset:
            return Response('[]')
        data = StringIO.StringIO()
        classificator = self.project.classificator
        rdf = prepare_results_table(queryset, data, classificator, return_df=True)
        params = self.get_extra_params()
        all_dep = params.pop('all_dep')
        
        if all_dep:
            deployments = Deployment.objects.filter(
                research_project=self.project.research_project
            ).values_list(
                'deployment_id', 'location__location_id', 'start_date',
                'end_date', 'location__coordinates'
            )
        else:
            deployments = queryset.values_list(
                'resource__deployment__deployment_id',
                'resource__deployment__location__location_id',
                'resource__deployment__start_date',
                'resource__deployment__end_date',
                'resource__deployment__location__coordinates'
            ).order_by().distinct()
            
        deployments = [
            (k[0], k[1], k[2], k[3], k[4].x, k[4].y) for k in deployments
        ]
        ddf = pandas.DataFrame(
            deployments, columns=[
                'deployment_id','location_id', 'start', 'end', 'x', 'y'
            ]
        )
        ddf = ddf.dropna()
        ddf['days'] = (ddf.end-ddf.start).dt.days.astype(np.int)
        ddf['start'] = ddf.start.dt.strftime('%Y-%m-%d %H:%M')
        ddf['end'] = ddf.end.dt.strftime('%Y-%m-%d %H:%M')

        geo = params.pop('geojson')
        params.update({
            'rdf': rdf, 'ddf': ddf
        })
        out = aggregate_results(**params)
        if geo:
            properties = out.drop(["x","y"], axis=1).columns
            out_geojson = df_to_geojson(out, properties, lat='y', lon='x')
            return Response(json.dumps(out_geojson))
        else:
            return Response(out.to_csv())


class ClassificationMapViewSet(ClassificationViewSet):
    pagination_class = None
    serializer_class = classification_serializers.ClassificationMapSerializer


class ClassificatorViewSet(PaginatedReadOnlyModelViewSet):
    """Returns a list of classificators.
    """
    permission_classes = (permissions.IsAuthenticated, )
    queryset = Classificator.objects.all()
    filter_class = ClassificatorFilter
    serializer_class = classification_serializers.ClassificatorSerializer
    search_fields = ['name', 'owner__username']

    def get_queryset(self):
        return Classificator.objects.get_accessible(
            user=self.request.user
        )


class ClassificationProjectViewSet(PaginatedReadOnlyModelViewSet):
    """Returns a list of classification projects.
    List of projects is limited only to those that are not marked as
    disabled (removed)
    """
    permission_classes = (permissions.IsAuthenticated, )
    queryset = ClassificationProject.objects.all()
    filter_class = ClassificationProjectFilter
    serializer_class = \
        classification_serializers.ClassificationProjectSerializer
    search_fields = ['name', 'owner__username', 'research_project__name']
    select_related = [
        'owner', 'classificator', 'research_project'
    ]

    def get_queryset(self):
        return ClassificationProject.objects.get_accessible(
            user=self.request.user
        ).filter(disabled_at__isnull=True).select_related(
            *self.select_related
        ).prefetch_related('classification_project_roles__user')


class ClassificationProjectCollectionViewSet(PaginatedReadOnlyModelViewSet):
    """Returns a list of classification project collections."""
    permission_classes = (permissions.IsAuthenticated, )
    queryset = ClassificationProjectCollection.objects.all()
    filter_class = ClassificationProjectCollectionFilter
    serializer_class = \
        classification_serializers.ClassificationProjectCollectionSerializer
    search_fields = [
        'collection__collection__name',
        'collection__collection__owner__username'
    ]

    def get_queryset(self):
        return ClassificationProjectCollection.objects.get_accessible(
            user=self.request.user
        ).prefetch_related(
            'collection__collection__managers',
            'collection__collection__owner',
            'project__owner', 'project__classificator',
        )


class SequenceViewSet(PaginatedReadOnlyModelViewSet):
    """Returns a list of sequences"""
    pagination_class = None
    permission_classes = (permissions.IsAuthenticated, )
    queryset = Sequence.objects.all()
    filter_class = SequenceFilter
    serializer_class = classification_serializers.SequenceReadSerializer
    search_fields = ['name', 'created_by__username']


class ClassificationResourcesViewSet(PaginatedReadOnlyModelViewSet):
    """Returns a list of classified resources within classification project
    for given classification project collection. It uses a custom
    pagination mechanism to limit a number of resources in a sequence
    returned to a user.

    Unauthenticated users get empty queryset
    """
    pagination_class = None
    default_size = 2
    permission_classes = (permissions.IsAuthenticated, )
    filter_class = ClassificationFilter
    serializer_class = \
        classification_serializers.ClassificationResourceSerializer
    select_related = [
        'resource', 'resource__deployment__location__timezone', 'sequence__sequence_id'
    ]

    def get_queryset(self):
        collection_pk = self.kwargs['collection_pk']
        collection = get_object_or_404(ClassificationProjectCollection, pk=collection_pk)
        user = self.request.user

        if user.is_authenticated():
            queryset = collection.classifications.all().select_related(
                *self.select_related
            ).prefetch_related('user_classifications__owner')
        else:
            queryset = Classification.objects.none()

        return queryset

    def list(self, request, *args, **kwargs):
        base_queryset = self.get_queryset()
        queryset = self.filter_queryset(base_queryset)
        pagination_data = {
            'total': base_queryset.count(),
            'filtered': queryset.count(),
        }
        resource_pk = self.kwargs['current_resource_pk']
        resource_obj = get_object_or_404(Resource, pk=resource_pk)

        # custom pagination based on current object
        try:
            size = int(self.request.GET['size'])
        except Exception:
            size = self.default_size
        qs_lte = queryset.filter(
            resource__date_recorded__lte=resource_obj.date_recorded
        ).values_list("pk", flat=True).order_by('-resource__date_recorded')[:size+1]
        qs_gt = queryset.filter(
            resource__date_recorded__gt=resource_obj.date_recorded
        ).values_list("pk", flat=True).order_by('resource__date_recorded')[:size]
        pks = list(qs_lte)
        pks.extend(list(qs_gt))
        queryset = queryset.filter(pk__in=pks).order_by('resource__date_recorded')
        serializer = self.get_serializer(queryset, many=True)
        response = {
            'pagination': pagination_data,
            'results': serializer.data
        }
        return Response(response)

view_classification_resources = ClassificationResourcesViewSet.as_view({'get':'list'})


class ClassificationImport(APIView):
    """
    Import classifications to existing classification project collections.

    **Example**:

    curl -D- -u alice@trapper.pl:alice -H "Accept: application/json" -H "Content-type: application/json" -X PUT -d
    "**Data** (see below for the example of data structure)" http://localhost:8000/api/classification_projects/results/add/

    **Data**:
    ```
    {
        "cproject_id": "1",
        "approve_all": "True",
        "classifications": [
            {
                "classification_id": "789",
                "data_static": {
                    "EMPTY": "True","FTYPE": "3","Quality": "Bad"
                },
                "data_dynamic": [
                    {
                        "Age": "Adult", "Number": "10", "Sex": "Female",
                        "annotations": "[]", "comments": "test", "species": "European Bison"
                    },
                    {
                        "Age": "Juvenile", "Number": "5", "Sex": "Female",
                        "annotations": "[]", "comments": "test", "species": "Wolf"
                    }
                ]
            }
        ]
    }
    ```
    """
    permission_classes = (permissions.IsAuthenticated, )

    def response_struct(self, data, errorcode, errorstring):
        return {
            'response': {
                'data': data,
                'status': errorcode,
                'errorstring': errorstring
            }
        }

    def add_error_msg(self, classification_pk, msg, errors_list):
        error = {"classification: {pk}".format(
            pk=classification_pk,
        ): msg}
        errors_list.append(error)

    def post(self, request, format=None):

        user = request.user
        timestamp = now()
        data = request.DATA
        errors_list = []
        total = 0

        try:
            cproject = ClassificationProject.objects.get(
                pk=data.get('cproject_id')
            )
            if cproject.can_update(user=user):
                static_attrs = cproject.classificator.get_static_attrs_order()
                dynamic_attrs = cproject.classificator.get_dynamic_attrs_order()
                form_fields = cproject.classificator.prepare_form_fields()

                data_classifications = data.get('classifications')
                if not data_classifications:
                    return Response(
                        self.response_struct(
                            None, 400, u"Bad request."
                        )
                    )
                total = len(data_classifications)
                data_classification_pks = [k['classification_id'] for k in data_classifications]
                classifications = Classification.objects.filter(
                    pk__in=data_classification_pks
                )
                classification_pks = [k.pk for k in classifications]

                # prepare variables to store data for further bulk create/update
                user_classifications = []
                cleaned_dynamic_rows = {}
                exclude_classification_pks = []

                for classification in data_classifications:

                    classification_pk = int(classification.get('classification_id'))

                    try:
                        pk = int(classification.get('classification_id'))
                    except ValueError, e:
                        msg = str(e)
                        self.add_error_msg(pk, msg, errors_list)
                        exclude_classification_pks.append(
                            classification_pk
                        )
                        continue
                    if not pk in classification_pks:
                        msg = 'Classification not found.'
                        self.add_error_msg(pk, msg, errors_list)
                        exclude_classification_pks.append(
                            classification_pk
                        )
                        continue

                    cleaned_dynamic_rows[classification_pk] = []
                    data_static = classification.get('data_static')
                    data_dynamic = classification.get('data_dynamic')

                    # validate static_attrs
                    if static_attrs:
                        static_form = ClassificationForm(
                            fields_defs=form_fields['S'],
                            attrs_order=static_attrs,
                            readonly=False,
                            data=data_static
                        )
                        if not static_form.is_valid():
                            self.add_error_msg(
                                classification_pk,
                                dict(static_form.errors.items()),
                                errors_list)
                            exclude_classification_pks.append(
                                classification_pk
                            )
                            continue

                    dynamic_loop_broke = False
                    #validate dynamic_attrs
                    if dynamic_attrs:
                        for dynamic_row in data_dynamic:
                            dynamic_form = ClassificationForm(
                                fields_defs=form_fields['D'],
                                attrs_order=dynamic_attrs,
                                readonly=False,
                                data=dynamic_row
                            )
                            if not dynamic_form.is_valid():
                                dynamic_loop_broke = True
                                self.add_error_msg(
                                    classification_pk,
                                    dict(dynamic_form.errors.items()),
                                    errors_list)
                                exclude_classification_pks.append(
                                    classification_pk
                                )
                                break

                            cleaned_dynamic_rows[classification_pk].append(
                                dynamic_form.cleaned_data
                            )

                        # executes the following block if there is no break in the inner loop
                        # i.e. if there is no "dynamic_attrs" to process or if all dynamic rows
                        # have been successfully validated
                        if dynamic_loop_broke:
                            continue

                        user_classification = UserClassification(
                            classification_id=classification_pk,
                            owner=user,
                            created_at=timestamp,
                            updated_at=timestamp,
                        )
                        if static_attrs:
                            user_classification.static_attrs = static_form.cleaned_data
                            user_classifications.append(user_classification)

                # exclude invalid data
                classifications = classifications.exclude(pk__in=exclude_classification_pks)

                # bulk delete UserClassification objects
                UserClassification.objects.filter(
                    classification__in=classifications, owner=user
                ).delete()

                # bulk create UserClassification objects
                UserClassification.objects.bulk_create(user_classifications)

                user_classifications = list(UserClassification.objects.filter(
                    classification__in=classifications, owner=user
                ).values_list('pk', 'classification__pk', 'static_attrs'))

                # bulk delete ClassificationDynamicAttrs objects
                ClassificationDynamicAttrs.objects.filter(
                    classification__in=classifications
                ).delete()

                # bulk create UserClassificationDynamicAttrs
                dynamic_attrs_objects = []
                for uc in user_classifications:
                    for dynamic_row in cleaned_dynamic_rows[uc[1]]:
                        dynamic_attrs_objects.append(
                            UserClassificationDynamicAttrs(
                                userclassification_id=uc[0],
                                attrs=dynamic_row
                            )
                        )
                UserClassificationDynamicAttrs.objects.bulk_create(dynamic_attrs_objects)

                if data.get('approve_all'):
                    # bulk create ClassificationDynamicAttrs objects
                    dynamic_attrs_objects = []
                    for c in classifications:
                        for dynamic_row in cleaned_dynamic_rows[c.pk]:
                            dynamic_attrs_objects.append(
                                ClassificationDynamicAttrs(
                                    classification_id=c.pk,
                                    attrs=dynamic_row
                                )
                            )
                    ClassificationDynamicAttrs.objects.bulk_create(dynamic_attrs_objects)

                # if classifications should be approved do it by updating
                # Classification objects
                if data.get('approve_all'):
                    # first use the queryset api to update values common for all objects
                    classifications.update(
                        status=True, approved_by=user, approved_at=timestamp
                    )
                    # next bulk_update other, objects specific values
                    classifications = list(classifications)
                    classifications.sort(key=lambda x: x.pk)
                    user_classifications.sort(key=lambda x: x[1])
                    i = 0
                    for classification in classifications:
                        classification.approved_source_id = user_classifications[i][0]
                        if static_attrs:
                            classification.static_attrs = user_classifications[i][2]
                        i += 1
                    bulk_update(classifications, update_fields=[
                        'approved_source_id', 'static_attrs'
                    ])

                summary = {
                    'totalClassifications': total,
                    'successfullyImported': total - len(errors_list),
                    'errors': len(errors_list)
                }

                return Response(
                    self.response_struct(
                        summary, 201, errors_list
                    )
                )
            else:
                return Response(
                    self.response_struct(
                        None, 401, u"Permission denied."
                    )
                )
        except ClassificationProject.DoesNotExist:
            return Response(
                self.response_struct(
                    None, 404, u"Classification project does not exist."
                )
            )
        except ClassificationProjectCollection.DoesNotExist:
            return Response(
                self.response_struct(
                    None, 404, u"Classification project collection does not exist."
                )
            )
