#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from lxml import etree

class EMLGenerator:
    def __init__(self, eml_setup):
        """
        Set EML header and unique data table and creator ID
        """
        # Used for EML saving
        self.eml_setup_init = eml_setup
        self.eml_setup = eml_setup.get_setup()
        self.root = self.set_header()
        self.creator_id = self.eml_setup.get('creator_id')
        self.data_table_id = self.eml_setup.get('data_table_id')
        self.datetime_now = datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def set_header():
        """
        Set EML header
        """

        # Schema
        schema = 'eml://ecoinformatics.org/eml-2.1.1'
        schema_location = '{0} eml.xsd'.format(schema)

        # Namespace map
        nsmap = {
            'eml': 'eml://ecoinformatics.org/eml-2.1.1',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }

        return etree.Element(
            '{' + schema + '}eml',
            nsmap=nsmap,
            attrib={
                '{' + nsmap.get('xsi', None) + '}schemaLocation': schema_location,
                'packageId': '',
                'system': 'knb'
            }
        )

    def set_permission(self, principal='public', permission='read'):
        """
        Set permission block
        """

        access = etree.SubElement(self.root, 'access', attrib={'authSystem': 'knb', 'order': 'allowFirst'})
        allow = etree.SubElement(access, 'allow')

        etree.SubElement(allow, 'principal').text = principal
        etree.SubElement(allow, 'permission').text = permission

    @staticmethod
    def set_admin_personal_data(parent, personal_data):
        """
        Set Classification project admin personal data block
        """

        individual_name = etree.SubElement(parent, 'individualName')

        etree.SubElement(individual_name, 'givenName').text = personal_data.get('givenName')
        etree.SubElement(individual_name, 'surName').text = personal_data.get('surName')
        etree.SubElement(parent, 'organizationName').text = personal_data.get('organizationName')
        etree.SubElement(parent, 'positionName').text = personal_data.get('positionName')

        address = etree.SubElement(parent, 'address')

        etree.SubElement(address, 'deliveryPoint').text = personal_data.get('deliveryPoint')
        etree.SubElement(address, 'city').text = personal_data.get('city')
        etree.SubElement(address, 'administrativeArea').text = personal_data.get('administrativeArea')
        etree.SubElement(address, 'postalCode').text = personal_data.get('postalCode')
        etree.SubElement(address, 'country').text = personal_data.get('country')
        etree.SubElement(parent, 'phone', attrib={'phonetype': 'voice'}).text = personal_data.get('phone')
        etree.SubElement(parent, 'electronicMailAddress').text = personal_data.get('electronicMailAddress')

    def set_admins(self, dataset_root):
        """
        Set data block for all Classification Project admins
        """

        # Creator
        creator = etree.SubElement(dataset_root, 'creator')
        self.set_contact(dataset_root)

        # Associated party
        associated_party = etree.SubElement(dataset_root, 'associatedParty')

        # All Classification Project admins
        admins = self.eml_setup.get('project_admins')

        if admins:
            for admin in admins:
                if admin.get('eml_creator'):
                    self.set_admin_personal_data(parent=creator, personal_data=admin)
                else:
                    self.set_admin_personal_data(parent=associated_party, personal_data=admin)

    def set_contact(self, dataset_root):
        """
        Set contact block
        """

        contact = etree.SubElement(dataset_root, 'contact')
        etree.SubElement(contact, 'references').text = self.creator_id

    def set_coverage(self, dataset_root):
        """
        Set coverage block with Geographic, Temporal and Taxonomic data
        """

        coverage = etree.SubElement(dataset_root, 'coverage')

        # Geographic (bounding coordinate) coverage
        geographic_coverage = etree.SubElement(coverage, 'geographicCoverage')
        geographic_coverage_dict = self.eml_setup.get('coverage').get('geographic_coverage')

        if geographic_coverage_dict:
            etree.SubElement(geographic_coverage, 'geographicDescription').text = geographic_coverage_dict.get(
                'geographicDescription'
            )

            bounding_coordinates = etree.SubElement(geographic_coverage, 'boundingCoordinates')

            etree.SubElement(bounding_coordinates, 'westBoundingCoordinate').text = geographic_coverage_dict.get(
                'westBoundingCoordinate'
            )
            etree.SubElement(bounding_coordinates, 'eastBoundingCoordinate').text = geographic_coverage_dict.get(
                'eastBoundingCoordinate'
            )
            etree.SubElement(bounding_coordinates, 'northBoundingCoordinate').text = geographic_coverage_dict.get(
                'northBoundingCoordinate'
            )
            etree.SubElement(bounding_coordinates, 'southBoundingCoordinate').text = geographic_coverage_dict.get(
                'southBoundingCoordinate'
            )

        # Temporal coverage
        temporal_coverage = etree.SubElement(coverage, 'temporalCoverage')
        range_of_dates = etree.SubElement(temporal_coverage, 'rangeOfDates')
        begin_date = etree.SubElement(range_of_dates, 'beginDate')
        temporal_coverage_dict = self.eml_setup.get('coverage').get('temporal_coverage')

        etree.SubElement(begin_date, 'calendarDate').text = temporal_coverage_dict.get('beginDate')
        end_date = etree.SubElement(range_of_dates, 'endDate')

        etree.SubElement(end_date, 'calendarDate').text = temporal_coverage_dict.get('endDate')

        # Taxonomic coverage
        taxonomic_coverage = etree.SubElement(coverage, 'taxonomicCoverage')
        taxonomic_coverage_dict = self.eml_setup.get('coverage').get('taxonomic_coverage')

        for species in taxonomic_coverage_dict:
            taxonomic_classification_level_0 = etree.SubElement(
                taxonomic_coverage, 'taxonomicClassification'
            )
            etree.SubElement(taxonomic_classification_level_0, 'taxonRankName').text = species.get(
                'taxonRankName_level_0'
            )
            etree.SubElement(taxonomic_classification_level_0, 'taxonRankValue').text = species.get(
                'taxonRankValue_level_0'
            )

            taxonomic_classification_level_1 = etree.SubElement(
                taxonomic_classification_level_0, 'taxonomicClassification'
            )
            etree.SubElement(taxonomic_classification_level_1, 'taxonRankName').text = species.get(
                'taxonRankName_level_1'
            )
            etree.SubElement(taxonomic_classification_level_1, 'taxonRankValue').text = species.get(
                'taxonRankValue_level_1'
            )

            taxonomic_classification_level_2 = etree.SubElement(
                taxonomic_classification_level_1, 'taxonomicClassification'
            )
            etree.SubElement(taxonomic_classification_level_2, 'taxonRankName').text = species.get(
                'taxonRankName_level_2'
            )
            etree.SubElement(taxonomic_classification_level_2, 'taxonRankValue').text = species.get(
                'taxonRankValue_level_2'
            )
            etree.SubElement(taxonomic_classification_level_2, 'commonName').text = species.get(
                'commonName_level_2'
            )

    def set_methods(self, dataset_root):
        """
        Set method block
        """

        # Method step
        methods = etree.SubElement(dataset_root, 'methods')
        methods_dict = self.eml_setup.get('methods')
        method_step = etree.SubElement(methods, 'methodStep')
        description = etree.SubElement(method_step, 'description')
        section = etree.SubElement(description, 'section')

        # Currently we have only one methodStep
        # For more than one need to add loop
        etree.SubElement(section, 'title').text = methods_dict.get('methodStep').get('title')
        etree.SubElement(section, 'para').text = methods_dict.get('methodStep').get('para')
        etree.SubElement(method_step, 'instrumentation')

        # Sampling
        sampling = etree.SubElement(methods, 'sampling')
        study_extent = etree.SubElement(sampling, 'studyExtent')
        description = etree.SubElement(study_extent, 'description')

        etree.SubElement(description, 'para')

        sampling_description = etree.SubElement(sampling, 'samplingDescription')

        etree.SubElement(sampling_description, 'para')

    @staticmethod
    def set_attribute_beginning(attributes_root, attribute_data):
        """
        Set beginning for all attribute blocks
        """

        attribute = etree.SubElement(attributes_root, 'attribute')
        attribute_data = attribute_data.get('data')

        etree.SubElement(attribute, 'attributeName').text = attribute_data.get('attributeName')
        etree.SubElement(attribute, 'attributeDefinition').text = attribute_data.get('attributeDefinition')
        etree.SubElement(attribute, 'storageType', attrib={'typeSystem': 'Python'}).text = attribute_data.get(
            'storageType'
        )

        measurement_scale = etree.SubElement(attribute, 'measurementScale')

        return measurement_scale

    def set_attribute_integer_or_float(self, attributes_root, attribute_data):
        """
        Set rest of the block for integer / float attribute
        """

        measurement_scale = self.set_attribute_beginning(attributes_root, attribute_data)
        attribute_data = attribute_data.get('data')
        interval = etree.SubElement(measurement_scale, 'interval')
        unit = etree.SubElement(interval, 'unit')

        etree.SubElement(unit, 'standardUnit').text = attribute_data.get('standardUnit')

        numeric_domain = etree.SubElement(interval, 'numericDomain')

        etree.SubElement(numeric_domain, 'numberType').text = attribute_data.get('numberType')

    def set_attribute_string(self, attributes_root, attribute_data):
        """
        Set rest of the block for string / boolean / select-list attribute
        """

        measurement_scale = self.set_attribute_beginning(attributes_root, attribute_data)
        attribute_data = attribute_data.get('data')
        nominal = etree.SubElement(measurement_scale, 'nominal')
        non_numeric_domain = etree.SubElement(nominal, 'nonNumericDomain')
        values = attribute_data.get('values')
        values_length = len(values) if values else 0

        # For nominal-list
        if values and values_length > 1:
            enumerated_domain = etree.SubElement(non_numeric_domain, 'enumeratedDomain')

            for index, val in enumerate(values):
                if index == 0:
                    code_definition = etree.SubElement(enumerated_domain, 'codeDefinition')

                etree.SubElement(code_definition, 'code').text = val.get('code')
                etree.SubElement(code_definition, 'definition').text = val.get('definition')
        # For nominal-freeform
        elif values_length == 1:
            text_domain = etree.SubElement(non_numeric_domain, 'textDomain')

            etree.SubElement(text_domain, 'definition').text = attribute_data.get('attributeDefinition')
        else:
            text_domain = etree.SubElement(non_numeric_domain, 'textDomain')

            etree.SubElement(text_domain, 'definition').text = attribute_data.get('definition')

    def set_attribute_comment(self, attributes_root, attribute_data):
        """
        Set rest of the block for comment attribute
        """

        measurement_scale = self.set_attribute_beginning(attributes_root, attribute_data)
        attribute_data = attribute_data.get('data')
        nominal = etree.SubElement(measurement_scale, 'nominal')
        non_numeric_domain = etree.SubElement(nominal, 'nonNumericDomain')
        text_domain = etree.SubElement(non_numeric_domain, 'textDomain')

        etree.SubElement(text_domain, 'definition').text = attribute_data.get('definition')

    def set_attribute_datetime_list(self, attributes_root, attribute_data):
        """
        Set rest of the block for datetime attribute
        """

        measurement_scale = self.set_attribute_beginning(attributes_root, attribute_data)
        attribute_data = attribute_data.get('data')
        datetime_block = etree.SubElement(measurement_scale, 'dateTime')

        etree.SubElement(datetime_block, 'formatString').text = attribute_data.get('formatString')
        etree.SubElement(datetime_block, 'dateTimePrecision').text = attribute_data.get('dateTimePrecision')

    def set_data_table_header(self, dataset_root, attrs_set):
        """
        Set header dataTable block
        """

        data_table = etree.SubElement(dataset_root, 'dataTable')

        etree.SubElement(data_table, 'entityName').text = attrs_set.get('entityName')
        etree.SubElement(data_table, 'entityDescription').text = attrs_set.get('entityDescription')

        physical = etree.SubElement(data_table, 'physical')

        etree.SubElement(physical, 'objectName').text = attrs_set.get('objectName')
        etree.SubElement(physical, 'size', attrib={'unit': 'byte'}).text = attrs_set.get('size')

        data_format = etree.SubElement(physical, 'dataFormat')
        text_format = etree.SubElement(data_format, 'textFormat')

        etree.SubElement(text_format, 'attributeOrientation').text = attrs_set.get(
            'attributeOrientation'
        )

        simple_delimited = etree.SubElement(text_format, 'simpleDelimited')

        etree.SubElement(simple_delimited, 'fieldDelimiter').text = attrs_set.get('fieldDelimiter')

        return data_table

    def set_attributes(self, data_table, attrs_set):
        """
        Set all attributes block in attributeList
        """

        attributes_list = etree.SubElement(data_table, 'attributeList')
        attributes = attrs_set.get('attributes')

        if attributes:
            for attribute in attributes:
                attribute_type = attribute.get('data').get('storageType')

                # If attribute has Integer (integer) or Float (real) type
                if attribute_type in ('integer', 'float', 'real'):
                    self.set_attribute_integer_or_float(attributes_root=attributes_list, attribute_data=attribute)

                # If attribute has String type
                if attribute_type == 'string':
                    self.set_attribute_string(attributes_root=attributes_list, attribute_data=attribute)

                # If attribute has Comment type
                if attribute_type == 'comment':
                    self.set_attribute_comment(attributes_root=attributes_list, attribute_data=attribute)

                # If attribute has datetime (datetime-list) type
                if attribute_type == 'list':
                    self.set_attribute_datetime_list(attributes_root=attributes_list, attribute_data=attribute)

    def set_results_table(self, dataset_root):
        """
        """
        results_attrs = self.eml_setup.get('results_attrs')
        data_table = self.set_data_table_header(dataset_root, results_attrs)
        self.set_attributes(data_table, results_attrs)
        etree.SubElement(data_table, 'numberOfRecords').text = results_attrs.get('numberOfRecords')

    def set_deployments_table(self, dataset_root):
        """
        """
        deployments_attrs = self.eml_setup.get('deployments_attrs')
        if deployments_attrs:
            data_table = self.set_data_table_header(dataset_root, deployments_attrs)
            self.set_attributes(data_table, deployments_attrs)
            etree.SubElement(data_table, 'numberOfRecords').text = deployments_attrs.get('numberOfRecords')

    def set_dataset(self):
        """
        Set all dataset block (main part)
        """

        dataset = etree.SubElement(self.root, 'dataset')

        # Research project and Classification project names
        etree.SubElement(dataset, 'title').text = self.eml_setup.get('title')

        # Publication date
        etree.SubElement(dataset, 'pubDate').text = self.eml_setup.get('pubDate')

        # Classification project admins
        self.set_admins(dataset)

        # Research project abstract
        abstract = etree.SubElement(dataset, 'abstract')

        etree.SubElement(abstract, 'para').text = self.eml_setup.get('abstract')

        # Research project keywords
        keyword_set = etree.SubElement(dataset, 'keywordSet')
        keywords = self.eml_setup.get('keywords')

        if keywords:
            for key in keywords:
                etree.SubElement(keyword_set, 'keyword').text = key

        # Intellectual rights
        intellectual_rights = etree.SubElement(dataset, 'intellectualRights')

        etree.SubElement(intellectual_rights, 'para')

        # Geographic, temporal and taxonomic
        self.set_coverage(dataset)

        # Methods
        self.set_methods(dataset)

        # Data table (results)
        self.set_results_table(dataset)

        # Data table (deployments, optional)
        self.set_deployments_table(dataset)


    def save_as_xml(self):
        """
        Generate and save final XML file
        """

        self.set_permission()
        self.set_dataset()

        with open(os.path.join(self.eml_setup_init.media_dir, 'EML-{0}-{1}.xml'.format(
                self.eml_setup_init.classification_project.pk,
                self.datetime_now
        )), 'w') as f:
            f.write(etree.tostring(
                self.root,
                xml_declaration=True,
                pretty_print=True,
                encoding='utf-8'
            ))

        return f.name
