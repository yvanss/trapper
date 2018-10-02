from __future__ import absolute_import

import dateutil
import pytz
from celery import shared_task
from django.contrib.gis.geos import Point
from django.utils import timezone

from trapper.apps.geomap.models import Location, Deployment


class LocationImporter():

    def __init__(self, data, user):
        self.data = data
        self.user = user
        self.csv = data.get('csv_file')
        self.gpx = data.get('gpx_data')
        self.df = data.get('df')
        self.research_project = data.get('research_project')
        self.timezone = data.get('timezone')
        if self.csv:
            self.total = len(self.df)
        if self.gpx:
            self.total = len(self.gpx.waypoints)
        self.imported = 0
        self.log = []

    def import_location(
            self, location_id, x, y, name='', description='',
    ):

        error_msg = '<strong>[ERROR] </strong>Location ID, {loc_id} '.format(
            loc_id=location_id
        )
        try:
            location = Location.objects.get(
                location_id=location_id,
                research_project=self.research_project
            )
            if not location.can_update(user=self.user):
                self.log.append(error_msg)
                self.log.append(
                    'You are not allowed to update this location.'
                )
                return 1

        except Location.DoesNotExist:
            location = Location(
                location_id=location_id,
                research_project=self.research_project,
                date_created=timezone.now(),
                owner=self.user,
                is_public=False
            )
        try:
            coords = Point((float(x),float(y)), srid=4326)
        except Exception as e:
            self.log.append(error_msg)
            self.log.append(
                'Error when parsing coordinates: {e}'.format(e=str(e))
            )
            return 1
        location.coordinates = coords
        location.timezone = self.timezone
        location.name = name
        location.description = description
        location.save()
        return 0

    def import_gpx(self):
        """Parse gpx data
        """
        for waypoint in self.gpx.waypoints:
            status = self.import_location(
                location_id=waypoint.name,
                x=waypoint.longitude,
                y=waypoint.latitude
            )
            if status == 1:
                continue
            else:
                self.imported += 1

    def import_csv(self):
        """Parse csv data
        """
        for i in range(0, len(self.df)):
            location_id = self.df.iloc[i]['location_id']
            x = self.df.iloc[i]['X']
            y = self.df.iloc[i]['Y']
            name = ''
            if 'name' in self.df.columns:
                name = self.df.iloc[i]['name']
            description = ''
            if 'description' in self.df.columns:
                description = self.df.iloc[i]['description']

            status = self.import_location(
                location_id=location_id,
                x=x, y=y, name=name,
                description=description
            )
            if status == 1:
                continue
            else:
                self.imported += 1

    def import_locations(self):
        if self.csv:
            self.import_csv()
        elif self.gpx:
            self.import_gpx()
        else:
            return self.log

        if self.imported == 0:
            self.log.insert(0,
                'The celery task is finished. Unfortunately none of the locations '
                'could be imported. See errors below.<br>'
            )
        else:
            self.log.insert(0,
                'You have successfully imported <strong>{imported}</strong> '
                'out of <strong>{total}</strong> locations.<br>'
                .format(
                    imported=self.imported,
                    total=self.total
                )
            )
        return self.log

    def run_with_logger(self):
        log = self.import_locations()
        log = '<br>'.join(log)
        return log


@shared_task
def celery_import_locations(data, user):
    """
    Celery task that imports locations from csv or gpx file.
    """
    importer = LocationImporter(data, user)
    log = importer.run_with_logger()
    return log


class DeploymentImporter():

    def __init__(self, data, user):
        self.data = data
        self.user = user
        self.df = data.get('df')
        self.total = len(self.df)
        self.imported = 0
        self.log = []

    def import_deployments(self):
        research_project = self.data['research_project']
        tz = self.data['timezone']

        for i in range(0, len(self.df)):
            deployment_id = self.df.iloc[i]['deployment_id']
            location_id = self.df.iloc[i]['location_id']

            error_msg = '<strong>[ERROR] </strong>{i}, Deployment ID, {dep_id} '.format(
                dep_id=deployment_id, i=i
            )

            # first check if deployment's location exists
            try:
                location = Location.objects.get(
                    location_id=location_id,
                    research_project=research_project
                )
            except Location.DoesNotExist, e:
                self.log.append(error_msg)
                self.log.append(str(e))
                continue

            deployment_code = self.df.iloc[i]['deployment_code']
            deployment_start = self.df.iloc[i]['deployment_start']
            deployment_end = self.df.iloc[i]['deployment_end']
            correct_setup = self.df.iloc[i]['correct_setup'] == 'True'
            correct_tstamp = self.df.iloc[i]['correct_tstamp'] == 'True'

            # try to parse datetime objects and make them timezone aware
            try:
                start = dateutil.parser.parse(deployment_start)
                if start.tzinfo:
                    start = start.astimezone(pytz.UTC)
                else:
                    start = tz.localize(start).astimezone(pytz.UTC)
            except Exception, e:
                self.log.append(error_msg)
                self.log.append(str(e))
                start = None
            try:
                end = dateutil.parser.parse(deployment_end)
                if end.tzinfo:
                    end = end.astimezone(pytz.UTC)
                else:
                    end = tz.localize(end).astimezone(pytz.UTC)
            except Exception, e:
                self.log.append(error_msg)
                self.log.append(str(e))
                end= None

            # create/update deployment
            try:
                deployment = Deployment.objects.get(
                    deployment_id=deployment_id,
                    research_project=research_project,
                )
                if not deployment.can_update(user=self.user):
                    self.log.append(error_msg)
                    self.log.append(
                        'You are not allowed to update this deployment.'
                    )
                    continue

            except Deployment.DoesNotExist:
                deployment = Deployment(
                    deployment_id=deployment_id,
                    research_project=research_project,
                    date_created=timezone.now(),
                    owner=self.user,
                )
            deployment.location=location
            deployment.deployment_code=deployment_code
            deployment.start_date=start
            deployment.end_date=end
            deployment.correct_setup=correct_setup
            deployment.correct_tstamp=correct_tstamp
            if 'view_quality' in self.df.columns:
                deployment.view_quality = self.df.iloc[i]['view_quality']
            if 'comments' in self.df.columns:
                deployment.comments = self.df.iloc[i]['comments']
            deployment.save()
            self.imported += 1

        if self.imported == 0:

            self.log.insert(0,
                'The celery task is finished. Unfortunately none of the deployments '
                'could be imported. See errors below.<br>'
            )

        else:

            self.log.insert(0,
                'You have successfully imported <strong>{imported}</strong> '
                'out of <strong>{total}</strong> deployments.<br>'
                .format(
                    imported=self.imported,
                    total=self.total
                )
            )

        return self.log

    def run_with_logger(self):
        log = self.import_deployments()
        log = '<br>'.join(log)
        return log


@shared_task
def celery_import_deployments(data, user):
    """
    Celery task that imports deployments from csv file.
    """
    importer = DeploymentImporter(data, user)
    log = importer.run_with_logger()
    return log
