# -*- coding: utf-8 -*-
"""
Celery configuration requires that all tasks that should be available for
asynchronous processing should be created in `tasks.py` file
"""
from __future__ import absolute_import

import os
import datetime
import zipfile
import pandas
from shutil import rmtree

from celery import shared_task
from bulk_update.helper import bulk_update

from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.conf import settings

from trapper.apps.media_classification.forms import ClassificationForm
from trapper.apps.media_classification.models import (
    Classification, UserClassification,
    ClassificationDynamicAttrs, UserClassificationDynamicAttrs,
    Sequence, SequenceResourceM2M
)
from trapper.apps.media_classification.views.api import prepare_results_table
from trapper.apps.geomap.models import Deployment
from trapper.apps.geomap.serializers import DeploymentTableSerializer
from trapper.apps.common.tools import datetime_aware
from trapper.apps.accounts.utils import (
    get_external_data_packages_path, create_external_media
)
from trapper.apps.accounts.models import UserDataPackage
from trapper.apps.accounts.taxonomy import PackageType, ExternalStorageSettings
from trapper.apps.media_classification.eml.eml_conts import EMLSetup
from trapper.apps.media_classification.eml.eml_generator import EMLGenerator


class ClassificationImporter():

    def __init__(self, data, user):
        self.data = data
        self.user = user
        self.timestamp = now()
        self.project = data.get('project')
        self.static_attrs = self.project.classificator.get_static_attrs_order()
        self.dynamic_attrs = self.project.classificator.get_dynamic_attrs_order()
        self.form_fields = self.project.classificator.prepare_form_fields()
        self.results_df = data.get('results_df', None)
        self.dynamic_df = self.results_df[['id']+self.dynamic_attrs]
        self.dynamic_df = self.dynamic_df.dropna()
        self.static_df = self.results_df.drop(self.dynamic_attrs, axis=1)
        self.static_df = self.static_df.drop_duplicates() 
        self.total = len(self.static_df)
        self.imported = 0
        self.log = []

    def add_error_msg(self, classification_id, msg):
        self.log.append(
            '<strong>[ERROR] </strong>'
            'Classification ID {clas_id}:'
            .format(clas_id=classification_id)
        )
        self.log.append(msg)

    def import_classifications(self):
        classifications_data = self.static_df.id.tolist()
        classifications = Classification.objects.filter(
            pk__in=classifications_data,
            project=self.project
        )
        classifications_pks = [k.pk for k in classifications]

        # prepare variables to store data for further bulk create/update
        user_classifications = []
        cleaned_dynamic_rows = {}
        exclude_classification_pks = []

        for i in range(0, len(self.static_df)):
            dynamic_loop_broke = False
            try:
                classification_id = int(self.static_df.iloc[i]['id'])
            except ValueError, e:
                msg = str(e)
                self.add_error_msg(classification_id, msg)
                exclude_classification_pks.append(classification_id)
                continue
            if classification_id not in classifications_pks:
                msg = 'Classification does not exist.'
                self.add_error_msg(classification_id, msg)
                exclude_classification_pks.append(classification_id)
                continue

            static_data = self.static_df.iloc[i][self.static_attrs]

            if self.static_attrs and self.static_df is not None:

                static_form = ClassificationForm(
                    fields_defs=self.form_fields['S'],
                    attrs_order=self.static_attrs,
                    readonly=False,
                    data=static_data.to_dict()
                )

                if not static_form.is_valid():
                    msg = str(static_form.errors)
                    self.add_error_msg(classification_id, msg)
                    exclude_classification_pks.append(classification_id)
                    continue

            if self.dynamic_attrs and self.dynamic_df is not None:
                cleaned_dynamic_rows[classification_id] = []
                dynamic_df_rows = self.dynamic_df[
                    (self.dynamic_df.id == str(classification_id))
                ]

                if len(dynamic_df_rows):
                    for j in range(0, len(dynamic_df_rows)):
                        dynamic_data_row = dynamic_df_rows.iloc[j][self.dynamic_attrs]

                        dynamic_form = ClassificationForm(
                            fields_defs=self.form_fields['D'],
                            attrs_order=self.dynamic_attrs,
                            readonly=False,
                            data=dynamic_data_row.to_dict()
                        )
                        if not dynamic_form.is_valid():
                            dynamic_loop_broke = True
                            msg = str(dynamic_form.errors)
                            self.add_error_msg(classification_id, msg)
                            exclude_classification_pks.append(classification_id)
                            break

                        cleaned_dynamic_rows[classification_id].append(
                            dynamic_form.cleaned_data
                        )

            # executes the following block if there is no break in the inner loop
            # i.e. if there is no "dynamic_attrs" to process or if all dynamic rows
            # have been successfully validated
            if dynamic_loop_broke:
                continue

            user_classification = UserClassification(
                classification_id=classification_id,
                owner=self.user,
                created_at=self.timestamp,
                updated_at=self.timestamp,
            )
            if self.static_attrs:
                user_classification.static_attrs = static_form.cleaned_data
                user_classifications.append(user_classification)

            self.imported += 1

        # exclude invalid data
        classifications = classifications.exclude(pk__in=exclude_classification_pks)

        if classifications:
            # bulk delete UserClassification objects
            UserClassification.objects.filter(
                classification__in=classifications, owner=self.user
            ).delete()

            # bulk create UserClassification objects
            UserClassification.objects.bulk_create(user_classifications)

            user_classifications = list(UserClassification.objects.filter(
                classification__in=classifications, owner=self.user
            ).values_list('pk', 'classification__pk', 'static_attrs'))

            if self.dynamic_attrs and self.dynamic_df is not None:
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

                if self.data.get('approve_all'):
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
            if self.data.get('approve_all'):
                # first use the queryset api to update values common for all objects
                classifications.update(
                    status=True, approved_by=self.user, approved_at=self.timestamp
                )
                # next bulk_update other, objects specific values
                classifications = list(classifications)
                classifications.sort(key=lambda x: x.pk)
                user_classifications.sort(key=lambda x: x[1])
                i = 0
                for classification in classifications:
                    classification.approved_source_id = user_classifications[i][0]
                    if self.static_attrs:
                        classification.static_attrs = user_classifications[i][2]
                    i += 1
                bulk_update(classifications, update_fields=[
                    'approved_source_id', 'static_attrs'
                ])

        if self.imported == 0:

            self.log.insert(0,
                'The celery task is finished. Unfortunately none of the classifications '
                'could be imported. See errors below.<br>'
            )

        else:

            self.log.insert(0,
                'You have successfully imported <strong>{imported}</strong> '
                'out of <strong>{total}</strong> classifications.<br>'
                .format(
                    imported=self.imported,
                    total=self.total
                )
            )

        self.log.insert(0,
            'Classification project: <strong>{project}</strong>'
            .format(
                project=self.project.name
            )
        )

        return self.log

    def run_with_logger(self):
        log = self.import_classifications()
        log = '<br>'.join(log)
        return log

@shared_task
def celery_import_classifications(data, user):
    """
    Celery task that imports classifications from csv files into given
    classification project.
    """
    importer = ClassificationImporter(data, user)
    log = importer.run_with_logger()
    return log


class SequencesBuilder():

    def __init__(self, data, user):
        self.data = data
        self.user = user
        self.total = None
        self.processed_collections = 0
        self.log = []

    def group_resources(self, resources, delta):
        resources.sort(key=lambda x: x.date_recorded)
        groups = []
        group = []
        res_len = len(resources)
        for i in range(res_len-1):
            diff = resources[i+1].date_recorded - resources[i].date_recorded
            if diff <= delta:
                group.append(resources[i])
                if i+2 == res_len:
                    group.append(resources[i+1])
                    groups.append(group)
            else:
                if group:
                    group.append(resources[i])
                    groups.append(group)
                    group = []
        return groups

    def create_sequences(self, cp_collection, groups):
        description = 'Built automatically. The time interval set to {interval} minutes.'.format(
            interval=self.data['time_interval']
        )
        for group in groups:
            sequence = Sequence(
                collection=cp_collection,
                created_by=self.user,
                created_at=datetime_aware(),
                description=description,
            )
            sequence.save()
            try:
                seq_res_objects = []
                for resource in group:
                    obj = SequenceResourceM2M(
                        sequence=sequence,
                        resource=resource
                    )
                    obj.full_clean()
                    seq_res_objects.append(obj)
            except ValidationError, e:
                self.log.insert(str(e))
                sequence.delete()
                seq_res_objects = []
                continue
            else:
                for obj in seq_res_objects:
                    obj.save()
                # update classification objects with
                # sequence data
                sequence.classifications.clear()
                classifications = Classification.objects.filter(
                    collection=cp_collection,
                    resource__in=group
                )
                classifications.update(sequence=sequence)

    def process_data(self):
        delta = datetime.timedelta(
            minutes=self.data.get('time_interval')
        )
        dep_aggr = self.data.get('deployments')
        cp_collections = self.data.get('project_collections')
        self.total = len(cp_collections)
        for cp_collection in cp_collections:
            overwrite = self.data.get('overwrite')
            if overwrite:
                Sequence.objects.filter(collection=cp_collection).delete()
            resources = cp_collection.get_resources(user=self.user)
            if dep_aggr:
                deployments = Deployment.objects.filter(resources__in=resources)
                for d in list(set(deployments)):
                    resources_d = [k for k in resources if k.deployment == d]
                    groups = self.group_resources(resources_d, delta)
                    self.create_sequences(cp_collection, groups)
            else:
                groups = self.group_resources(resources, delta)
                self.create_sequences(cp_collection, groups)
            self.processed_collections += 1

        if self.processed_collections == 0:
            self.log.insert(0,
                'The celery task is finished. Unfortunately none of the specified '
                'classification project collections could be processed. See '
                'the errors below.<br>'
            )
        else:
            self.log.insert(0,
                'You have successfully built sequences for <strong>{cols}</strong> '
                'out of <strong>{total}</strong> classification project collections.<br>'
                .format(
                    cols=self.processed_collections,
                    total=self.total
                )
            )

        return self.log

    def run_with_logger(self):
        log = self.process_data()
        log = '<br>'.join(log)
        return log


@shared_task
def celery_build_sequences(data, user):
    """
    Celery task to automatically build sequences of resources.
    """
    importer = SequencesBuilder(data, user)
    log = importer.run_with_logger()
    return log


class TagsCreator():

    def __init__(self, data, user):
        self.data = data
        self.user = user
        self.total = None
        self.log = []

    def create_tags(self):
        classifications = self.data.get('classifications', None)
        tag_keys = self.data.get('tag_keys', None)

        for classification in classifications:
            resource = classification.resource
            classification_tags = []
            static_attrs = classification.static_attrs
            dynamic_attrs = classification.dynamic_attrs.all()

            for key, val in static_attrs.iteritems():
                if key in tag_keys:
                    classification_tags.append(val)

            for attrs in dynamic_attrs:
                for key, val in attrs.attrs.iteritems():
                    if key in tag_keys:
                        classification_tags.append(val)

            resource.tags.add(*classification_tags)
        self.log.append(
            'You have successfully created tags for {n} resources'.format(
                n=len(classifications)
            )
        )
        return self.log

    def run_with_logger(self):
        log = self.create_tags()
        log = '<br>'.join(log)
        return log


@shared_task
def celery_create_tags(data, user):
    """
    Celery task to automatically create tags for selected resources
    based on their classifications.
    """
    tags_creator = TagsCreator(data, user)
    log = tags_creator.run_with_logger()
    return log


class ResultsDataPackageGenerator():

    def __init__(self, data, user, project):
        self.data = data
        self.user = user
        self.project = project
        # prepare querysets for serializers
        self.classifications = self.project.classifications.all().select_related(
            'resource__deployment__location', 'sequence'
        ).prefetch_related(
            'dynamic_attrs'
        )
        if self.data.get('deployments'):
            self.deployments = Deployment.objects.filter(
                resources__classifications__project=self.project
            ).distinct().select_related(            
                'location',
            )
        self.timestamp = now()
        self.timestamp_str = self.timestamp.strftime('%d%m%Y_%H%M%S')
        self.package_name = "results_{0}_{1}.zip".format(
            self.project.pk, self.timestamp_str
        )
        self.package_path_base = get_external_data_packages_path(
            user.username
        )
        if not os.path.exists(self.package_path_base):
            create_external_media(user.username)
        self.package_path = os.path.join(
            self.package_path_base, self.package_name
        )
        # prepare names for data tables
        self.results_table_filename = 'ResultsTable-{0}-{1}.csv'.format(
            self.project.pk, self.timestamp_str
        )
        if self.data.get('deployments'):
            self.deployments_table_filename = 'DeploymentsDataTable-{0}-{1}.csv'.format(
                self.project.pk, self.timestamp_str
            )
        else:
            self.deployments_table_filename = None
        self.tmp_path = os.path.join(self.package_path_base, self.timestamp_str)
        if not os.path.exists(self.tmp_path):
            os.mkdir(self.tmp_path)

    def get_results_table(self):
        output_filepath = os.path.join(
            self.tmp_path, self.results_table_filename
        )
        prepare_results_table(
            self.classifications,
            output_filepath,
            self.project.classificator
        )

    def get_deployments_table(self):
        data = DeploymentTableSerializer(
            self.deployments, many=True).data
        df = pandas.DataFrame(data)
        output_filepath = os.path.join(
            self.tmp_path, self.deployments_table_filename
        )
        df.to_csv(output_filepath, encoding='utf-8')

    def generate_eml(self):
        eml_setup = EMLSetup(
            self.tmp_path,
            self.project,
            self.results_table_filename,
            self.deployments_table_filename
        )
        eml = EMLGenerator(eml_setup)
        eml.save_as_xml()

    def run(self):
        self.get_results_table()
        if self.data.get('deployments'):
            self.get_deployments_table()
        if self.data.get('eml_file'):
            self.generate_eml()

        with zipfile.ZipFile(self.package_path, 'w') as zipf:
            for filename in os.listdir(self.tmp_path):
                filepath = os.path.join(self.tmp_path, filename)
                zipf.write(filepath, filename)
            zipf.close()

        user_data_package_obj = UserDataPackage(
            user=self.user, date_created=self.timestamp,
            package_type=PackageType.CLASSIFICATION_RESULTS
        )
        user_data_package_obj.package.name = os.path.join(
            self.user.username,
            ExternalStorageSettings.DATA_PACKAGES,
            self.package_name
        )
        user_data_package_obj.save()

        # remove temporary files
        rmtree(self.tmp_path)

        msg = (
            'The requested data package: <strong>{name}</strong> '
            'has been successfully generated.'
        )
        return msg.format(
            name=self.package_name
        )


@shared_task
def celery_results_to_data_package(data, user, project):
    """
    Celery task that create a data package (archive) containing the
    results of selected classification project.

    :param resources: queryset of storage.Resource model
    """
    
    gen = ResultsDataPackageGenerator(data, user, project)
    log = gen.run()
    return log
    
