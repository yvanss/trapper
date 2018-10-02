# -*- coding: utf-8 -*-
import os
from datetime import datetime

from django.utils.html import strip_tags

from trapper.apps.storage.taxonomy import ResourceType
from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectRoleLevels
)
from trapper.apps.geomap.models import Location
from trapper.apps.extra_tables.models import Species


class EMLSetup:
    def __init__(
            self, media_dir,
            classification_project,
            results_table_filename,
            deployments_table_filename=None
    ):
        """
        Data initialization:

        - get Research and Classification project objects;
        - get Classificator object;
        - get all classifications;
        - set some consts.
        """

        # Consts - feel free to set them up
        self.creator_id = u''
        self.data_table_id = u''
        self.geographicDescription = u'Geographic description'
        self.method_step_title = u'MethodStep1'
        self.number_standard_unit = u'dimensionless'
        self.comments_definition = u'comments, extra notes'
        self.annotation_format_string = u'[hh:mm:ss, hh:mm:ss]'
        self.annotation_datetime_precision = u'1 second'
        # Cannot be a unicode
        self.delimiter = ','
        self.datetime_now = datetime.now().strftime('%Y-%m-%d')
        self.media_dir = media_dir
        self.results_table_filename = results_table_filename
        self.deployments_table_filename = deployments_table_filename

        # Research project
        self.research_project = classification_project.research_project
        # Classification project
        self.classification_project = classification_project
        # Classificator
        self.classificator = self.classification_project.classificator
        # Classifications
        self.classifications = self.classification_project.classifications.all().order_by(
            'resource__pk')

        self.fields_type = {
            'B': 'string',
            'F': 'real',
            'I': 'integer',
            # Normal string, select-list or species predefined attrs
            'S': 'string',
            # Comments predefined attrs
            'C': 'comment',
            # Annotations predefined attrs
            'A': 'list',
        }

        # Parse HStore attributes structure to Python dict
        # custom_attrs and predefined_attrs contains extra information about the attributes
        self.custom_attrs = self.classificator.parse_hstore_values('custom_attrs')
        self.predefined_attrs = self.classificator.parse_hstore_values('predefined_attrs')

        self.static_attrs = self.classificator.get_static_attrs_order()
        self.dynamic_attrs = self.classificator.get_dynamic_attrs_order()
        self.attrs_all_ordered = self.static_attrs + self.dynamic_attrs 

    def get_abstract(self):
        """
        Return Research project abstract
        """
        return strip_tags(self.research_project.abstract).strip() if self.research_project.abstract else None

    def get_keywords(self):
        """
        Return Research project keywords
        """

        return [keyword.name for keyword in self.research_project.keywords.all()]

    def get_project_admins(self):
        """
        Return admins list
        """
        admins = []

        for role in self.classification_project.classification_project_roles.all():
            user_profile = role.user.userprofile
            admin_dict = {}
            # eml_creator key is True when the admin is EML creator
            if role.name == ClassificationProjectRoleLevels.ADMIN:
                admin_dict['eml_creator'] = True
            else:
                admin_dict['eml_creator'] = False
            admin_dict['givenName'] = role.user.first_name
            admin_dict['surName'] = role.user.last_name
            admin_dict['organizationName'] = user_profile.institution
            admin_dict['electronicMailAddress'] = role.user.email
            admins.append(admin_dict)
        return admins

    def get_geographic_coverage(self):
        """
        Calculate and return geographic coverage
        """
        locations_ids = set(self.classifications.values_list(
            'resource__deployment__location__pk', flat=True
        ))
        # Filter location and  calculate the extent
        locations = Location.objects.filter(pk__in=locations_ids)
        if locations.exists():
            extent = locations.extent()
            if extent:
                geographic_coverage = {
                    'geographicDescription': self.geographicDescription,
                    'westBoundingCoordinate': str(extent[0]),
                    'southBoundingCoordinate': str(extent[1]),
                    'eastBoundingCoordinate': str(extent[2]),
                    'northBoundingCoordinate': str(extent[3]),
                }
                return geographic_coverage
            else:
                return None
        else:
            return None

    def get_temporal_coverage(self):
        """
        Calculate and return temporal coverage
        """
        dates_recorded = self.classifications.values_list('resource__date_recorded')
        temporal_coverage = {
            'beginDate': min(dates_recorded)[0].strftime('%Y-%m-%d'),
            'endDate': max(dates_recorded)[0].strftime('%Y-%m-%d')
        }
        return temporal_coverage

    def get_taxonomic_coverage(self):
        """
        Return taxonomic coverage only for Species selected in Classificator
        """
        selected_species = self.predefined_attrs.get('selected_species', None)
        taxonomic_coverage = []
        if selected_species:
            species = Species.objects.filter(pk__in=selected_species)
            for single_species in species:
                species_taxonomic_coverage = {
                    'taxonRankName_level_0': u'Family',
                    'taxonRankValue_level_0': single_species.family,
                    'taxonRankName_level_1': u'Genus',
                    'taxonRankValue_level_1': single_species.genus,
                    'taxonRankName_level_2': u'Species',
                    'taxonRankValue_level_2': single_species.latin_name,
                    'commonName_level_2': single_species.english_name
                }
                taxonomic_coverage.append(species_taxonomic_coverage)
        return taxonomic_coverage

    def get_method_step(self):
        """
        Return method step with Research project method description
        """
        method_step = {
            'title': self.method_step_title,
            'para': strip_tags(self.research_project.methods).strip() if self.research_project.methods else None
        }
        return method_step

    def get_results_attrs(self):
        """
        Return data attributes
        """
        single_attr = {
            'entityName': self.results_table_filename,
            'entityDescription': u'Results attributes',
            'objectName': self.results_table_filename,
            'size': str(os.path.getsize(os.path.join(self.media_dir, self.results_table_filename))),
            'attributeOrientation':  u'column',
            'fieldDelimiter': self.delimiter,
            'attributes': []
        }

        if self.classifications:

            # classification_id
            single_attribute = {
                'data': {
                    'attributeName': u'id',
                    'attributeDefinition': (
                        u'This column is used as a unique identifier of resource '
                        u'belonging to particular classification project\'s collection.'
                    ),
                    'storageType': u'integer',
                    'standardUnit': self.number_standard_unit,
                    'numberType': u'integer',
                }
            }
            single_attr['attributes'].append(single_attribute)

            # resource_id
            single_attribute = {
                'data': {
                    'attributeName': u'resource_id',
                    'attributeDefinition': u'Resource ID (database)',
                    'storageType': u'integer',
                    'standardUnit': self.number_standard_unit,
                    'numberType': u'integer',
                }
            }
            single_attr['attributes'].append(single_attribute)

            # deployment_id
            single_attribute = {
                'data': {
                    'attributeName': 'deployment_id',
                    'attributeDefinition': u'Deployment ID.',
                    'storageType': u'integer',
                    'standardUnit': self.number_standard_unit,
                    'numberType': u'integer',
                }
            }
            single_attr['attributes'].append(single_attribute)

            # resource_name
            single_attribute = {
                'data': {
                    'attributeName': 'resource_name',
                    'attributeDefinition': u'The name of resource.',
                    'storageType': u'string',
                }
            }
            single_attr['attributes'].append(single_attribute)

            # resource_type
            single_attribute = {
                'data': {
                    'attributeName': 'resource_type',
                    'attributeDefinition': u'The type of resource.',
                    'storageType': u'string',
                    'values': []
                }
            }
            values_list = single_attribute['data'].get('values')
            for key,value in ResourceType.CHOICES:
                values_list.append({
                    'code': key,
                    'definition': value
                })
            single_attr['attributes'].append(single_attribute)

            # date_recorded
            single_attribute = {
                'data': {
                    'attributeName': 'date_recorded',
                    'attributeDefinition': u'The date and time (UTC) when resource was recorded.',
                    'storageType': u'string',
                }
            }
            single_attr['attributes'].append(single_attribute)

            # sequence_id
            single_attribute = {
                'data': {
                    'attributeName': 'sequence_id',
                    'attributeDefinition': u'Sequence ID.',
                    'storageType': u'integer',
                    'standardUnit': self.number_standard_unit,
                    'numberType': u'integer',
                }
            }
            single_attr['attributes'].append(single_attribute)

            attrs_all = [
                (attr, self.custom_attrs.get(attr)) for attr in self.attrs_all_ordered 
            ]

            for attrs in attrs_all:
                attr_name, attr_value = attrs
                attr_settings = self.custom_attrs.get(attr_name, None)

                # Resource ID
                single_attribute = {}

                # Custom attrs
                if attr_settings:
                    attr_sign = attr_settings.get('field_type')

                    data_type = self.fields_type.get(attr_sign)
                # Predefined attrs
                else:
                    attr_settings = {}

                    if self.predefined_attrs.get(attr_name):
                        if attr_name == u'species':
                            attr_sign = 'S'
                        elif attr_name == u'comments':
                            attr_sign = 'C'
                        elif attr_name == u'annotations':
                            attr_sign = 'A'

                        data_type = self.fields_type.get(attr_sign)
                    else:
                        # Predefined attrs which is not supported
                        attr_sign = None

                # Float and Integer
                if attr_sign in (u'F', u'I'):
                    single_attribute['data'] = {
                        'attributeName': attr_name,
                        'attributeDefinition': attr_settings.get('description', None),
                        'storageType': u'float' if data_type == 'real' else data_type,
                        'standardUnit': self.number_standard_unit,
                        'numberType': data_type,
                    }
                # Boolean and String
                elif attr_sign in (u'B', u'S'):
                    single_attribute['data'] = {
                        'attributeName': attr_name,
                        'attributeDefinition': attr_settings.get('description', None),
                        'storageType': data_type,
                        'values': []
                    }

                    values_list = single_attribute['data'].get('values')

                    if attr_sign == u'S':
                        # Custom select-list
                        if not self.predefined_attrs.get(attr_name):
                            select_list_values = [attr.strip() for attr in attr_value.get('values').split(',')]
                        # Species list
                        else:
                            selected_species = self.predefined_attrs.get('selected_species')

                            select_list_values = [
                                species.latin_name for species in Species.objects.filter(pk__in=selected_species)
                            ]

                        for value in select_list_values:
                            values_list.append({
                                'code': value,
                                'definition': value
                            })
                    else:
                        values_list.append({
                            'code': 'False',
                            'definition': 'False',
                        })
                        values_list.append({
                            'code': 'True',
                            'definition': 'True',
                        })
                # Comments
                elif attr_sign == u'C':
                    single_attribute['data'] = {
                        'attributeName': attr_name,
                        'attributeDefinition': attr_settings.get('description', None),
                        'storageType': data_type,
                        'definition': self.comments_definition
                    }
                # Annotation
                elif attr_sign == u'A':
                    single_attribute['data'] = {
                        'attributeName': attr_name,
                        'attributeDefinition': attr_settings.get('description', None),
                        'storageType': data_type,
                        'formatString': self.annotation_format_string,
                        'dateTimePrecision': self.annotation_datetime_precision
                    }
                else:
                    # Predefined attr which is not supported
                    single_attribute['data'] = {}

                single_attr['attributes'].append(single_attribute)

        single_attr['numberOfRecords'] = ''

        return single_attr

    def get_deployments_attrs(self):
        """
        Return deployments table attributes
        """
        
        if not self.deployments_table_filename:
            return None

        single_deployment_attr = {
            'entityName': self.deployments_table_filename,
            'entityDescription': u'Deployments data',
            'objectName': self.deployments_table_filename,
            'size': str(os.path.getsize(os.path.join(self.media_dir, self.deployments_table_filename))),
            'attributeOrientation':  u'column',
            'fieldDelimiter': self.delimiter,
            'attributes': []
        }

        if self.classifications:

            # deployment_id
            single_attribute = {
                'data': {
                    'attributeName': 'collection_id',
                    'attributeDefinition': (
                        u'Deployment ID is a unique combination of "deployment_code" and "location_id".'
                    ),
                    'storageType': u'integer',
                    'standardUnit': self.number_standard_unit,
                    'numberType': u'integer',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

            # deployment_code
            single_attribute = {
                'data': {
                    'attributeName': 'deployment_code',
                    'attributeDefinition': u'Deployment code.',
                    'storageType': u'string',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

            # deployment_start
            single_attribute = {
                'data': {
                    'attributeName': 'deployment_start',
                    'attributeDefinition': u'The date and time (UTC) when deployment started.',
                    'storageType': u'string',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

            # deployment_end
            single_attribute = {
                'data': {
                    'attributeName': 'deployment_end',
                    'attributeDefinition': u'The date and time (UTC) when deployment finished.',
                    'storageType': u'string',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

            # location_id
            single_attribute = {
                'data': {
                    'attributeName': 'location_id',
                    'attributeDefinition': u'Location ID.',
                    'storageType': u'string',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

            # location_X
            single_attribute = {
                'data': {
                    'attributeName': 'location_X',
                    'attributeDefinition': u'X coordinate (WSG84, EPSG:4326).',
                    'storageType': u'string',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

            # location_Y
            single_attribute = {
                'data': {
                    'attributeName': 'location_Y',
                    'attributeDefinition': u'Y coordinate (WSG84, EPSG:4326).',
                    'storageType': u'string',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

            # research_project
            single_attribute = {
                'data': {
                    'attributeName': 'research_project',
                    'attributeDefinition': u'The parent research project.',
                    'storageType': u'string',
                }
            }
            single_deployment_attr['attributes'].append(single_attribute)

        single_deployment_attr['numberOfRecords'] = ''

        return single_deployment_attr

    def get_setup(self):
        """
        Build and return the main structure which is used by EML generator
        """

        eml_setup = {
            'title': u'{0} : {1}'.format(self.research_project.name, self.classification_project.name),
            'pubDate': self.datetime_now,
            'abstract': self.get_abstract(),
            'keywords': self.get_keywords(),
            'creator_id': self.creator_id,
            'data_table_id': self.data_table_id,
            'project_admins': self.get_project_admins(),
            'coverage': {
                'geographic_coverage': self.get_geographic_coverage(),
                'temporal_coverage': self.get_temporal_coverage(),
                'taxonomic_coverage': self.get_taxonomic_coverage()
            },
            'methods': {
                'methodStep': self.get_method_step()
            },
            'results_attrs': self.get_results_attrs(),
            'deployments_attrs': self.get_deployments_attrs()
        }

        return eml_setup
