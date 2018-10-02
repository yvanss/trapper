import logging
from optparse import make_option
from django.core.management.base import BaseCommand
from trapper.apps.storage.models import Resource

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger('generate_thumbnails')


class Command(BaseCommand):
    """Base command class to handle all this stuff"""

    option_list = BaseCommand.option_list + (
        make_option(
            '--all',
            action='store_true',
            default=None,
            help='(Re)generate thumbnails for all resources. By default only '\
            'resources with missing thumbnails are selected.'
        ),
    )

    def __init__(self):
        super(Command, self).__init__()
        self.resources = Resource.objects.all()


    def handle(self, *args, **options):
        all_res = options['all']
        resources = self.resources

        if not all_res:
            LOGGER.info(u"Generating missing thumbnails only.")
            resources = [
                r for r in resources if not bool(r.file_thumbnail)
            ]
        else:
            LOGGER.info(u"(Re)generating thumbnails for all resources.")
        N = len(resources)
        LOGGER.info(u"Found {number} resources.".format(
            number=N
        ))
        i = 1
        for r in resources:
            LOGGER.info(u"RESOURCE {i}/{N}: {resource}".format(
                resource=r.name, i=i, N=N
            ))
            r.generate_thumbnails()
            i += 1
