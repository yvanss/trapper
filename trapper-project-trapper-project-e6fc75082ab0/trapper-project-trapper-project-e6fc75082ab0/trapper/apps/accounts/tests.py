# -*- coding: utf-8 -*-

import os

from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.lorem_ipsum import words

from trapper.apps.common.utils.identity import create_hashcode
from trapper.apps.common.utils.test_tools import ExtendedTestCase
from trapper.apps.accounts.taxonomy import ExternalStorageSettings

User = get_user_model()


class UserRegistrationTestCase(ExtendedTestCase):
    """Tests related to user registration"""

    def setUp(self):
        super(UserRegistrationTestCase, self).setUp()
        self.email = 'amanda@somedomain.com'
        self.passwd = 'amanda'
        os.environ['RECAPTCHA_TESTING'] = 'True'

    def tearDown(self):
        del os.environ['RECAPTCHA_TESTING']
        super(UserRegistrationTestCase, self).tearDown()

    def register_user(self):
        """Handler for registering user using signup"""
        url = reverse('account_signup')

        response = self.client.post(
            url,
            {
                'email': self.email,
                'password1': self.passwd,
                'password2': self.passwd,
                'g-recaptcha-response': 'PASSED'
            }
        )
        return response

    def activate_user(self, email):
        user = User.objects.get(email=email)
        user.is_active = True
        user.save()
        return user

    def test_register_account_inactive(self):
        """Newly registered user should be inactive"""
        self.assertFalse(User.objects.filter(email=self.email).exists())

        response = self.register_user()

        # redirect to inactive page
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email=self.email)
        self.assertFalse(user.is_active)

    def test_register_account_email_notification(self):
        """Registration of new user sends two emails, to admins and to user"""

        self.register_user()

        self.assertEqual(len(self.mail.outbox), 2)

        # First email is sent to user
        user_email = self.mail.outbox[0].to[0]

        self.assertEqual(user_email, self.email)

        # Second is sent to all admins
        admin_emails = self.mail.outbox[1].to

        for name, email in settings.ADMINS:
            self.assertIn(
                email,
                admin_emails,
                u"{name} is not in email receivers".format(name=name)
            )

    def test_register_account_activate(self):
        """Account activation sends email to user"""

        self.register_user()
        self.mail.outbox = []

        self.activate_user(email=self.email)

        self.assertEqual(len(self.mail.outbox), 1)
        self.assertEqual(self.mail.outbox[0].to[0], self.email)

    def test_register_external_dirs(self):
        """Account activation creates new directories for external media"""

        self.register_user()

        user = self.activate_user(email=self.email)
        for directory in ExternalStorageSettings.DIRS:
            self.assertTrue(
                os.path.exists(
                    os.path.join(
                        settings.EXTERNAL_MEDIA_ROOT, user.username, directory
                    )
                )
            )


class UserProfileTestCase(ExtendedTestCase):
    """Tests related to user registration"""

    def setUp(self):
        super(UserProfileTestCase, self).setUp()
        self.email = 'amanda@somedomain.com'
        self.passwd = 'amanda'

        self.user = User.objects.create_user(
            username='amanda',
            email=self.email,
            password=self.passwd,
        )

        self.profile_url = reverse('accounts:mine_profile')

    def test_profile_change(self):
        """Update user profile"""
        logged_in = self.client.login(
            username=self.user.username, password=self.passwd
        )

        self.assertTrue(logged_in)

        first_name = 'Amanda'
        last_name = 'Amandasia'
        institution = 'Hogwart'

        about_me = words(5)

        self.client.post(
            self.profile_url,
            data={
                'first_name': first_name,
                'last_name': last_name,
                'institution': institution,
                'about_me': about_me,
                'update-profile': ''
            }
        )

        user = User.objects.get(pk=self.user.pk)
        profile = user.userprofile

        self.assertEqual(user.first_name, first_name)
        self.assertEqual(user.last_name, last_name)
        self.assertEqual(profile.institution, institution)
        self.assertEqual(profile.about_me, about_me)

    def test_user_change_password(self):
        """
        After password has been changed user can authenticate with new one
        """

        # Auth with base passwd
        logged_in = self.client.login(
            username=self.user.username, password=self.passwd
        )
        self.assertTrue(logged_in)

        new_passwd = create_hashcode()
        self.client.post(
            self.profile_url,
            data={
                'old_password': self.passwd,
                'new_password1': new_passwd,
                'new_password2': new_passwd,
                'change-password': ''
            }
        )

        # After change passwd, old one stops working
        self.client.logout()
        logged_in = self.client.login(
            username=self.user.username, password=self.passwd
        )
        self.assertFalse(logged_in)

        # but new does
        logged_in = self.client.login(
            username=self.user.username, password=new_passwd
        )
        self.assertTrue(logged_in)

