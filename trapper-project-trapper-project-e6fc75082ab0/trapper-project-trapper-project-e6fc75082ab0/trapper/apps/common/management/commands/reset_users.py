import logging
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger('reset_users')


class Command(BaseCommand):
    """
    This is a command to reset all users data. It is supposed to be 
    used as CRON task to control trapper demo instances. the Superusers are
    excluded by default. To also exclude the Staff users set a flag "--keep-staff".
    """

    option_list = BaseCommand.option_list + (
        make_option(
            '--keep-staff',
            action='store_true',
            dest='keep_staff',
            default=None,
            help=(
                u'This flag prevents the staff users to be deleted.'
            ),
        ),
        make_option(
            '--limit-to-users',
            action='append',
            dest='limit_users',
            default=[],
            help=(
                u'Limit this action to provided users (list of pk).'
            ),
        ),
    )

    def __init__(self):
        super(Command, self).__init__()

    def get_users(self, keep_staff, limit_users=None):
        users = User.objects.exclude(is_superuser=True)
        if keep_staff:
            users = users.exclude(is_staff=True)
        if limit_users:
            users = users.filter(pk__in=limit_users)
        return users
        
    def handle(self, *args, **options):
        keep_staff = options['keep_staff']
        limit_users = options['limit_users']
        users = self.get_users(keep_staff, limit_users)
        for user in users:
            LOGGER.info(
                u"Deleting all data related to the user: {user}".format(
                    user=user.username
                )
            )
            # delete user's objects
            # start with resources as deployments
            # are linked with them through protected fkey
            user.owned_resources.all().delete()
            user.owned_deployments.all().delete()
            user.owned_locations.all().delete()
            user.owned_collections.all().delete() 	
            user.owned_maps.all().delete()
            user.userdatapackage_set.all().delete()
            user.research_projects.all().delete()
            user.user_classifications.all().delete()
            user.user_classificators.all().delete()
            user.resourceuserrate_set.all().delete()
            user.sent_messages.all().delete()
            user.received_messages.all().delete()
            user.usercomment_comments.all().delete()
            user.usertask_set.all().delete()
            user.my_collection_requests.all().delete()
            user.collection_requests.all().delete()
            
