#!/usr/bin/python
import os
import re
import logging
import datetime
import zipfile
from optparse import OptionParser, make_option
import yaml
from collections import OrderedDict
from PIL import Image
import pytz

logging.basicConfig(
    format='%(levelname)s:%(message)s',
    level=logging.DEBUG
)

# YAML mapping extension
_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return OrderedDict(loader.construct_pairs(node))

yaml.add_representer(OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)


class YAMLDefinitionGenerator(object):
    """
    """

    def __init__(
            self, data_dir, collections, yaml_path, timezone,
            video_ext='.mp4', video_extra_ext='.webm',
            image_ext='.JPG', project_name='',
    ):
        self.data_dir = data_dir
        self.collections = collections
        self.yaml_path = yaml_path
        self.timezone = timezone
        self.video_ext = video_ext
        self.video_extra_ext = video_extra_ext
        self.image_ext = image_ext
        self.project_name = project_name

    def get_collection_def(self, name):
        collection_def = OrderedDict()
        collection_def['name'] = name
        collection_def['project_name'] = self.project_name
        collection_def['resources_dir'] = name
        collection_def['deployments'] = []
        collection_def['resources'] = []
        return collection_def

    def get_deployment_def(self, deployment):
        deployment_def = OrderedDict()
        deployment_def['deployment_id']  = deployment
        deployment_def['resources'] = []
        return deployment_def

    def get_date_recorded(self, filepath):
        """
        The method to get datetime when resource was recorded under
        a simple assumption that this is a date of the last modification of
        recorded file. It returns UTC timestamp. In case of images it first
        tries to read 'DateTimeOriginal` EXIF tag.
        """
        if os.path.splitext(filepath)[1] == self.image_ext:
            try:
                t = Image.open(filepath)._getexif()[36867]
                t = datetime.datetime.strptime(t, '%Y:%m:%d %H:%M:%S')
                return str(self.timezone.localize(t).astimezone(pytz.utc))
            except (AttributeError, KeyError, IndexError, IOError, ValueError), e:
                t = os.path.getmtime(filepath)
        else:
            t = os.path.getmtime(filepath)
        return str(datetime.datetime.utcfromtimestamp(t))

    def get_resource_def(self, resource, resources_level):
        filepath = os.path.join(resources_level, resource)
        split_name = os.path.splitext(resource)
        resource_def = OrderedDict()
        resource_def['name'] = split_name[0]
        resource_def['file'] = resource
        extra_file = "".join([split_name[0], self.video_extra_ext])
        extra_file_path = os.path.join(resources_level, extra_file)
        extra_file_exists = os.path.exists(extra_file_path)
        if extra_file_exists:
            resource_def['extra_file'] = extra_file
        resource_def['date_recorded'] = self.get_date_recorded(filepath)
        return resource_def

    def filter_files(self, files):
        return [
            k for k in files if os.path.splitext(k)[1] in [
                self.video_ext, self.image_ext
            ]
        ]

    def build_data_dict(self):
        data_dict = OrderedDict()
        data_dict['collections'] = []
        collections_level = os.path.join(self.data_dir)
        for collection in  self.collections:
            # first create collection object
            collection_obj = self.get_collection_def(
                name=collection,
            )
            deployments_level = os.path.join(collections_level,collection)
            deployments = [
                k for k in os.listdir(deployments_level) if os.path.isdir(
                    os.path.join(deployments_level,k)
                )
            ]
            for deployment in deployments:
                deployment_obj = self.get_deployment_def(deployment)
                resources_level = os.path.join(deployments_level,deployment)
                resources = [
                    k for k in os.listdir(resources_level) if os.path.isfile(
                        os.path.join(resources_level,k)
                    )
                ]
                resources = self.filter_files(resources)
                for resource in resources:
                    resource_obj = self.get_resource_def(
                        resource, resources_level
                    )
                    deployment_obj['resources'].append(resource_obj)
                collection_obj['deployments'].append(deployment_obj)

            # "free" resources without assigned deployments
            resources = [
                k for k in os.listdir(deployments_level) if os.path.isfile(
                    os.path.join(deployments_level,k)
                )
            ]
            resources = self.filter_files(resources)
            for resource in resources:
                resource_obj = self.get_resource_def(
                    resource, deployments_level
                )
                collection_obj['resources'].append(resource_obj)

            data_dict['collections'].append(collection_obj)
        return data_dict

    def dump_yaml(self):
        f = open(self.yaml_path, 'w')
        data_dict = self.build_data_dict()
        yaml.dump(data_dict, f)


class GenerateDataPackage(object):
    """
    """

    def __init__(
            self, data_path, output_path, collections, timezone, 
            video_ext='.mp4', video_extra_ext='.webm',
            image_ext='.JPG', project=None
    ):
        self.ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        if not os.path.isdir(data_path):
            raise Exception('There is no directory: %s' % data_path)
        else:
            self.data_path = data_path
        if output_path and not os.path.isdir(output_path):
            raise Exception('There is no directory: %s' % output_path)
        else:
            self.output_path = output_path
        for collection in collections:
            collection_path = os.path.join(
                self.data_path, collection
            )
            if not os.path.isdir(collection_path):
                raise Exception('There is no directory: %s' % collection_path)
        self.collections = collections
        self.timezone = timezone

        logging.getLogger().addHandler(
            logging.FileHandler(
                self.get_package_name('.log')
            )
        )
        logging.info('Initializing data package generator...')
        self.video_ext = video_ext
        self.video_extra_ext = video_extra_ext
        self.image_ext = image_ext
        self.project = project

    def get_package_name(self, ext):
        if len(self.collections) == 1:
            return self.collections[0] + '_' + self.ts + ext
        else:
            return '_'.join(self.collections) + '_' + self.ts + ext

    def generate_yaml_definition(self):
        yaml_path = os.path.join(
            self.output_path,
            self.get_package_name('.yaml')
        )
        logging.info(
            'Generating data package definition file:\n%s',
            yaml_path
        )
        gen = YAMLDefinitionGenerator(
            data_dir=self.data_path,
            collections=self.collections,
            yaml_path=yaml_path,
            video_ext = self.video_ext,
            video_extra_ext=self.video_extra_ext,
            image_ext=self.image_ext,
            timezone=self.timezone,
            project_name=self.project
        )
        gen.dump_yaml()

    def filter_files(self, filenames):
        regexp = '.*\.?({video_ext}|{video_extra_ext}|{image_ext})'.format(
            video_ext=self.video_ext,
            video_extra_ext=self.video_extra_ext,
            image_ext=self.image_ext
        )
        return [
            k for k in filenames if re.match(
                regexp, k, re.IGNORECASE
            )
        ]

    def get_files(self):
        matches = []
        logging.info(
            'Collecting %s, %s and %s files...',
            self.video_ext, self.video_extra_ext, self.image_ext
        )
        for collection in self.collections:
            logging.info('Collection: %s', collection)
            collection_path = os.path.join(
                self.data_path, collection
            )
            for root, dirnames, filenames in os.walk(collection_path):
                for filename in self.filter_files(filenames):
                    matches.append(os.path.join(root, filename))
        logging.info('Found %s files in total.', len(matches))
        logging.info('')
        return matches

    def make_zip(self):
        files = self.get_files()
        zip_path = os.path.join(
            self.output_path,
            self.get_package_name('.zip')
        )
        logging.info('Building the zip archive: %s', zip_path)
        logging.info('')
        with zipfile.ZipFile(zip_path, 'w', allowZip64=True) as zip:
            for f in files:
                f_archive = re.sub('^'+self.data_path+os.path.sep+'?', '', f)
                logging.info('Adding file: %s', f_archive)
                zip.write(f, f_archive)


def main():
    title = 'Generate data package that can be uploaded using trapper web interface'
    usage = 'Usage: %prog [options] collection1 collection2 ...'
    option_list = [
        make_option(
            '--data-path',
            action='store',
            dest='data_path',
            help=('Data path i.e. directory with collections of resources as '
                  'its sub-directories. Each collection can have (optionally) '
                  'sub-directories aggregating resources into deployments.')
        ),
        make_option(
            '--output-path',
            action='store',
            dest='output_path',
            default='',
            help='Output path for generated data package.'
        ),
        make_option(
            '--video-ext',
            action='store',
            dest='video_ext',
            default='.mp4',
            help='Extension of video files (default: .mp4).'
        ),
        make_option(
            '--video-extra-ext',
            action='store',
            dest='video_extra_ext',
            default='.webm',
            help='Extension of extra video files (default: .webm).'
        ),
        make_option(
            '--image-ext',
            action='store',
            dest='image_ext',
            default='.JPG',
            help='Extension of image files (default: .JPG).'
        ),
        make_option(
            '--timezone',
            action='store',
            dest='timezone',
            default='',
            help=('Timezone code. See:'
                  'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
        ),
        make_option(
            '--project',
            action='store',
            dest='project',
            default='',
            help=('Acronym of the research project that uploaded '
                  'resources belong to.')
        ),
    ]
    parser = OptionParser(usage, option_list=option_list)
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error('You have to specify at least one collection you '
                     'want to include in a data package.')
    tz_error_msg = ('You have to specify a correct timezone. See:'
                    'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')
    if not options.timezone:
        parser.error(tz_error_msg)
    try:
        timezone = pytz.timezone(options.timezone)
    except (pytz.UnknownTimeZoneError, AttributeError):
        parser.error(tz_error_msg)
    logging.info('')
    logging.info(
        'Generating package started at %s',
        datetime.datetime.now()
    )
    logging.info('Output path: %s', options.output_path)
    logging.info('Collections: %s', ', '.join(args))
    logging.info('')
    gen = GenerateDataPackage(
        data_path=options.data_path,
        output_path=options.output_path,
        collections=args,
        video_ext=options.video_ext,
        video_extra_ext=options.video_extra_ext,
        image_ext=options.image_ext,
        timezone=timezone,
        project=options.project
    )
    gen.generate_yaml_definition()
    gen.make_zip()


if __name__ == "__main__":
    main()
