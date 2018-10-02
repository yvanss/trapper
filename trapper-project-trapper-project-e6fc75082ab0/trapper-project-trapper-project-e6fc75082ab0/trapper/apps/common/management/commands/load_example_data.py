# -*- coding: utf-8 -*-
"""
Command used to load example data into trapper database
"""

import os
import logging
import datetime
import random

from optparse import make_option

from leaflet_storage.models import Licence, TileLayer

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import Point
from django.contrib.webdesign.lorem_ipsum import sentence, words

# from trapper.apps.extra_tables.models import Species
from trapper.apps.storage.models import Resource, Collection
from trapper.apps.storage.taxonomy import ResourceStatus, CollectionStatus
from trapper.apps.common.tools import datetime_aware
from trapper.apps.messaging.models import Message
from trapper.apps.research.models import (
    ResearchProject,
    ResearchProjectRole,
    ResearchProjectCollection
)
from trapper.apps.research.taxonomy import (
    ResearchProjectRoleType, ResearchProjectStatus
)
from trapper.apps.media_classification.models import (
    Classificator, ClassificationProject, ClassificationProjectRole,
    ClassificationProjectCollection, Sequence, SequenceResourceM2M
)
from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectRoleLevels
)
from trapper.apps.geomap.models import Location
from trapper.apps.geomap.models import Deployment

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger('load_example_data')


class ResetDataException(CommandError):
    """Default exception for loading example data data"""
    pass


class Command(BaseCommand):
    """Base command class to handle all this stuff"""

    RESOURCES = 2
    COLLECTIOS = 10

    option_list = BaseCommand.option_list + (
        make_option(
            '--force-reset'
            action='store_true',
            default=None,
            help='Clear database before loading example data'
        ),
        make_option(
            '--simple-data',
            action='store_true',
            default=None,
            help='Load only users'
        ),
    )

    def __init__(self):
        super(Command, self).__init__()
        self.fixture = None
        self.menu_levels = []
        self.users = {}
        self.resources = {}
        self.collections = {}
        self.research_project = None
        self.research_project_role_admin = None
        self.research_project_role_expert = None
        self.research_project_collection_1 = None
        self.research_project_collection_2 = None
        self.research_project_collection_3 = None
        self.classification_project_1 = None
        self.classification_project_2 = None
        self.attributeset = None
        self.classification_project_collection_1 = None
        self.classification_project_collection_2 = None
        self.classification_project_collection_3 = None
        self.classification_project_role_1 = None
        self.classification_project_role_2 = None

    @classmethod
    def reset_data(cls):
        """Method responsible for clearing all data in project including
        users"""
        LOGGER.info(u" Data will be deleted before loading new one")
        LOGGER.info(u" > groups...")
        Group.objects.all().delete()
        LOGGER.info(u" > users...")
        User.objects.all().delete()

        LOGGER.info(u" > messages...")
        Message.objects.all().delete()
        LOGGER.info(u" > resources...")
        Resource.objects.all().delete()
        LOGGER.info(u" > collections...")
        Collection.objects.all().delete()

        LOGGER.info(u" > research projects...")
        ResearchProject.objects.all().delete()
        LOGGER.info(u" > research project roles...")
        ResearchProjectRole.objects.all().delete()
        LOGGER.info(u" > research project collections...")
        ResearchProjectCollection.objects.all().delete()

        LOGGER.info(u" > classification attributesets...")
        Classificator.objects.all().delete()
        LOGGER.info(u" > classification projects...")
        ClassificationProject.objects.all().delete()
        LOGGER.info(u" > classification project roles...")
        ClassificationProjectRole.objects.all().delete()
        LOGGER.info(u" > classification project collections...")
        ClassificationProjectCollection.objects.all().delete()

        LOGGER.info(u" > licences...")
        Licence.objects.all().delete()
        LOGGER.info(u" > tile layers...")
        TileLayer.objects.all().delete()
        LOGGER.info(u" > locations...")
        Location.objects.all().delete()
        LOGGER.info(u" > deployments...")
        Deployment.objects.all().delete()
        LOGGER.info(u" > sequences...")
        Sequence.objects.all().delete()

    def _create_user(self, username, is_staff=False, is_superuser=False):
        LOGGER.info(u"   - {username}".format(username=username))
        user, _created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': u"{username}@trapper.pl".format(username=username),
                'is_staff': is_staff,
                'is_superuser': is_superuser,
                'password': make_password(username)
            }
        )
        self.users[username] = user

    @classmethod
    def _get_random_datetime(cls):
        return datetime_aware(data=datetime.datetime(
            random.randint(2009, 2014),
            random.randint(1, 12),
            random.randint(1, 28),
            random.randint(0, 23),
            random.randint(0, 59),
            random.randint(0, 59)
        ))

    def load_users(self):
        """Load example users"""
        LOGGER.info(u" > users...")
        self._create_user(username='alice', is_staff=True, is_superuser=True)
        self._create_user(username='staff1')
        self._create_user(username='expert1')
        self._create_user(username='user1')
        self._create_user(username='user2')

    @staticmethod
    def load_groups():
        """Load example groups"""
        LOGGER.info(u" > groups...")

        LOGGER.info(u"   - Staff")
        staff_group, _created = Group.objects.get_or_create(name='Staff')
        staff_content_types = ContentType.objects.filter(
            app_label__in=[
                'media_classification', 'accounts', 'storage', 'auth'
            ]
        )
        staff_group.permissions = Permission.objects.filter(
            content_type__in=staff_content_types
        )

        LOGGER.info(u"   - Expert")
        expert_group, _created = Group.objects.get_or_create(name='Expert')
        expert_content_types = ContentType.objects.filter(
            app_label__in=['media_classification', 'storage']
        )
        expert_group.permissions = Permission.objects.filter(
            content_type__in=expert_content_types
        )

    def load_resources(self):
        """Load example resources"""
        LOGGER.info(u" > resources...")

        file_list = os.listdir('test_data/media_samples/')

        resource_filepath = "test_data/media_samples/"
        status_choices = [item[0] for item in ResourceStatus.CHOICES]

        for filename in file_list:
            for status in status_choices:
                for username, owner in self.users.items():
                    name = u"{file} {user} {status}".format(
                        file=filename.replace('.', '_'),
                        user=username,
                        status=status
                    )
                    resource = Resource.objects.create(
                        name=name,
                        owner=owner,
                        status=status,
                        date_recorded=Command._get_random_datetime(),
                        date_uploaded=Command._get_random_datetime(),
                    )
                    with open(resource_filepath + filename, 'rb') as res_file:
                        resource.file.save(
                            filename, File(res_file), save=False
                        )
                    resource.update_metadata(commit=True)
                    resource.generate_thumbnails()
                    self.resources[name] = resource

    def load_collections(self):
        """Load example collections"""
        LOGGER.info(u" > collections...")
        status_choices = [item[0] for item in CollectionStatus.CHOICES]

        for item in xrange(self.COLLECTIOS):
            collection = Collection.objects.create(
                name=sentence()[:30],
                owner=random.choice(self.users.values()),
                status=random.choice(status_choices),
            )
            collection.resources = Resource.objects.get_accessible(
                user=collection.owner
            )
            self.collections[collection.name] = collection

    def load_research_projects(self):
        """Load example research projects"""
        LOGGER.info(u" > research projects...")
        users = self.users.keys()
        research_project, _created = ResearchProject.objects.get_or_create(
            name="ResearchProject1",
            owner=self.users['alice'],
            status_date=datetime_aware(),
            status=ResearchProjectStatus.APPROVED,
        )
        self.research_project = research_project

    def load_research_project_roles(self):
        """Load example research project roles"""
        LOGGER.info(u" > research project roles...")
        self.research_project_role_admin, _created = \
            ResearchProjectRole.objects.get_or_create(
                name=ResearchProjectRoleType.ADMIN,
                user=self.users['alice'],
                project=self.research_project
            )
        self.research_project_role_expert, _created = \
            ResearchProjectRole.objects.get_or_create(
                name=ResearchProjectRoleType.EXPERT,
                user=self.users['alice'],
                project=self.research_project
            )

    def load_research_project_collections(self):
        """Load example research project collections"""
        LOGGER.info(u" > research project collections...")
        self.research_project_collection_1, _created = \
            ResearchProjectCollection.objects.get_or_create(
                project=self.research_project,
                collection=random.choice(
                    Collection.objects.filter(
                        owner=self.research_project.owner
                    )
                )
            )
        self.research_project_collection_2, _created = \
            ResearchProjectCollection.objects.get_or_create(
                project=self.research_project,
                collection=random.choice(
                    Collection.objects.filter(
                        owner=self.research_project.owner
                    )
                )
            )
        self.research_project_collection_3, _created = \
            ResearchProjectCollection.objects.get_or_create(
                project=self.research_project,
                collection=random.choice(
                    Collection.objects.filter(
                        owner=self.research_project.owner
                    )
                )
            )

    def load_classification_projects(self):
        """Load example classification projects"""
        LOGGER.info(u" > classification projects...")

        self.classification_project_1, _created = \
            ClassificationProject.objects.get_or_create(
                name="ClassificationProject1",
                research_project=self.research_project,
                owner=self.research_project.owner,
                classificator=self.attributeset,
            )
        self.classification_project_2, _created = \
            ClassificationProject.objects.get_or_create(
                name="ClassificationProject2",
                research_project=self.research_project,
                owner=self.research_project.owner,
                classificator=self.attributeset,
            )

    def load_attribute_sets(self):
        """Load example attribute sets"""
        LOGGER.info(u" > attribute sets...")
        predefined_attrs = {
            u'annotations': u'true',
            u'comments': u'true',
            u'required_annotations': u'false',
            u'required_comments': u'false',
            u'required_species': u'false',
            u'selected_species': u'[1, 2, 3, 4]',
            u'species': u'true',
            u'target_annotations': u'D',
            u'target_comments': u'D',
            u'target_species': u'D'
        }
        custom_attrs = {
            u'Age': (
                u'{"initial": "", "target": "D", "required": true, '
                u'"values": "Juvenile,Adult", "field_type": "S"}'
            ),
            u'EMPTY': (
                u'{"initial": "False", "target": "S", "required": false, '
                u'"values": "True,False", "field_type": "S"}'
            ),
            u'FTYPE': (
                u'{"initial": "3", "target": "S", "required": false, '
                u'"values": "1,2,3,4,5,6", "field_type": "S"}'
            ),
            u'Number': (
                u'{"initial": "1", "target": "D", "required": false, '
                u'"values": "", "field_type": "I"}'
            ),
            u'Quality': (
                u'{"initial": "Good", "target": "S", "required": false, '
                u'"values": "Terrible,Bad,Good,Excellent", "field_type": "S"}'
            ),
            u'Sex': (
                u'{"initial": "", "target": "D", "required": true, '
                u'"values": "Female,Male", "field_type": "S"}'
            )
        }
        dynamic_attrs_order = u'annotations,comments,species,Number,Age,Sex'
        static_attrs_order = u'FTYPE,Quality,EMPTY'
        self.attributeset, _created = Classificator.objects.get_or_create(
            name="test_attset",
            predefined_attrs=predefined_attrs,
            static_attrs_order=static_attrs_order,
            custom_attrs=custom_attrs,
            dynamic_attrs_order=dynamic_attrs_order,
            owner=self.users['alice'],
        )

    def load_classification_project_collections(self):
        """Load example classification project collections"""
        LOGGER.info(u" > classification project collections...")
        self.classification_project_collection_1, _created = \
            ClassificationProjectCollection.objects.get_or_create(
                project=self.classification_project_1,
                collection=self.research_project_collection_1,
                is_active=True
            )
        self.classification_project_collection_2, _creaetd = \
            ClassificationProjectCollection.objects.get_or_create(
                project=self.classification_project_1,
                collection=self.research_project_collection_2,
                is_active=True
            )
        self.classification_project_collection_3, _created = \
            ClassificationProjectCollection.objects.get_or_create(
                project=self.classification_project_1,
                collection=self.research_project_collection_3,
                is_active=False
            )

    def load_classification_project_roles(self):
        """Load example classification project roles"""
        LOGGER.info(u" > classification project roles...")
        self.classification_project_role_1 = \
            ClassificationProjectRole.objects.get_or_create(
                name=ClassificationProjectRoleLevels.ADMIN,
                user=self.users['alice'],
                classification_project=self.classification_project_1
            )
        self.classification_project_role_2 = \
            ClassificationProjectRole.objects.create(
                name=ClassificationProjectRoleLevels.EXPERT,
                user=self.users['alice'],
                classification_project=self.classification_project_1
            )

    def load_sequences(self):
        """Load example sequences"""
        LOGGER.info(u" > sequences...")
        resource_list = \
            self.research_project_collection_1.collection.resources.all()
        for counter in xrange(5):
            resources = random.sample(resource_list, random.randint(1, 5))

            sequence = Sequence.objects.create(
                sequence_id="S-{no}".format(no=counter),
                description=words(10),
                collection=self.classification_project_collection_1,
                created_at=Command._get_random_datetime(),
                created_by=self.users['alice']
            )
            for resource in resources:
                SequenceResourceM2M.objects.create(
                    sequence=sequence,
                    resource=resource
                )

    def load_locations(self):
        """Load example locations"""
        LOGGER.info(u" > locations...")
        users = self.users.keys()

        for pk in xrange(1, 100):
            location_id = u"ID_{num:02d}".format(num=pk)
            point_x = round(random.random(), 4) + random.randint(22, 23)
            point_y = round(random.random(), 4) + random.randint(52, 54)
            Location.objects.get_or_create(
                location_id=location_id,
                defaults={
                    'owner': self.users[random.choice(users)],
                    'is_public': random.choice([True, False]),
                    'coordinates': Point(point_x, point_y),
                }
            )

    def load_deployments(self):
        """Load example deployments"""
        LOGGER.info(u" > deployments...")
        user = self.users["alice"]
        locations = Location.objects.filter(owner=user)
        random_date1 = Command._get_random_datetime()
        random_date2 = Command._get_random_datetime()
        deployment_data = [("SESSION1", random_date1,
                            random_date1 + datetime.timedelta(days=10)),
                           ("SESSION2", random_date2,
                            random_date2 + datetime.timedelta(days=10))]

        for location in locations:
            random_dd = random.choice(deployment_data)
            Deployment.objects.get_or_create(
                location=location,
                deployment_code = random_dd[0],
                start_date = random_dd[1],
                end_date = random_dd[2],
                defaults={
                    'owner': user,
                    'date_created': datetime.datetime.now(),
                }
            )

    @staticmethod
    def load_resource_deployments():
        LOGGER.info(u" > link resources to deployments...")
        resources = Resource.objects.all()
        deployments = Deployment.objects.all()

        #sample_locations = random.sample(locations,  50)
        #sample_resources = resources
        for resource in resources:
            resource.deployment = random.choice(deployments)
            resource.save()

    @staticmethod
    def load_licences():
        LOGGER.info(u" > licenses...")
        Licence.objects.get_or_create(
            name=u'Basic licence',
            details=u'http://openstreetmap.com/'
        )

    @staticmethod
    def load_tile_layers():
        LOGGER.info(u" > tile layers...")
        TileLayer.objects.get_or_create(
            name=u'Mapa',
            url_template=u'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            minZoom=0,
            maxZoom=18,
            attribution=u'OSM',
        )

    def load_simple_data(self):
        """Method responsible for loading all data into database"""
        LOGGER.info(u" Loading base  data...")
        self.load_groups()
        self.load_users()
        # self.load_species()
        self.load_licences()
        self.load_tile_layers()
        self.load_locations()

    def load_data(self):
        """Method responsible for loading all data into database"""
        LOGGER.info(u" Loading example data...")
        self.load_simple_data()
        self.load_resources()
        self.load_deployments()
        self.load_resource_deployments()
        self.load_collections()
        self.load_research_projects()
        self.load_research_project_roles()
        self.load_research_project_collections()
        self.load_attribute_sets()
        self.load_classification_projects()
        self.load_classification_project_collections()
        self.load_classification_project_roles()
        self.load_sequences()

    def handle(self, *args, **options):
        """Decide what to do..."""
        force_reset = options['force_reset']
        simple_data = options['simple_data']

        if force_reset:
            Command.reset_data()

        if simple_data:
            self.load_simple_data()
        else:
            self.load_data()
