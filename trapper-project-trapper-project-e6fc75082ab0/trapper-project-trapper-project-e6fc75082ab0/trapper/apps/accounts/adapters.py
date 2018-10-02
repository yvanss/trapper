# -*- coding: utf-8 -*-
"""
Custom django-allauth adapter for creating user profiles which are
disabled by default. When profile is created admins get
email notification that user can be moderated
"""

from allauth.account.adapter import DefaultAccountAdapter

from django.core.mail import send_mail, mail_admins
from django.core.urlresolvers import reverse
from trapper.middleware import get_current_request
from django.contrib import messages
from django.utils import timezone
from django.conf import settings


class TrapperAdapter(DefaultAccountAdapter):
    """
    Custom allauth adapter for registration

    * User account is inactive by default
    * User gets email about registration
    * Admins gets email about user activation requirement
    * Message is added, so inactive user gets notification that account has
      been created and awaiting for approval
    """

    def get_login_redirect_url(self, request):
        """Default url used for redirection when user is logged in"""
        return reverse('accounts:dashboard')

    @staticmethod
    def get_admin_url(user):
        """Get full url to update user in admin based on user.pk"""
        request = get_current_request()
        return request.build_absolute_uri(
            reverse('admin:accounts_user_change', args=(user.pk,))
        )

    def send_email_notification(self, user):
        """Send emails:

        * to user
        * to admins
        """
        send_mail(
            subject=u'Your Trapper account has just been created!',
            message=(
                u'Dear {username},\n\n'
                u'You have successfully created your Trapper account. '
                u'However, your account is still inactive. When your account gets '
                u'activated we will notify you immediately.\n\n'
                u'Best regards,\n'
                u'Trapper Team'
            ).format(username=user.username.capitalize()),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True
        )
        mail_admins(
            u"New request for Trapper account",
            u"The following account needs your verification: {url}.".format(
                url=self.get_admin_url(user=user)
            )
        )

    def save_user(self, request, user, form, commit=True):
        """Make sure that user is inactive, and then send
        all necessary emails"""
        user = super(
            TrapperAdapter, self
        ).save_user(
            request=request, user=user, form=form, commit=False
        )
        user.is_active = False
        if commit:
            user.last_login = timezone.now() 
            user.save()

        if settings.EMAIL_NOTIFICATIONS:
            self.send_email_notification(user=user)

        messages.add_message(
            request,
            messages.SUCCESS,
            (u"You have successfully registered your account! Your request is "
             u"waiting for the final decision of Trapper administrators.")
        )
        return user
