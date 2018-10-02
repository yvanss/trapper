# -*- coding: utf-8 -*-

import threading
import pytz
from django.utils import timezone

_thread_locals = threading.local()


def get_current_request():
    """Function used to retrieve request associated with current thread"""
    return getattr(_thread_locals, 'request', None)


def get_current_user():
    """Function used to retrieve user stored in request associated with
    current thread"""
    request = get_current_request()
    return getattr(request, 'user', None)


class ThreadLocals(object):
    """Middleware that gets various objects from the
    request object and saves them in thread local storage."""

    def _clear_request(self):
        """Remove request data from local thread."""
        try:
            del _thread_locals.request
        except AttributeError:
            pass

    def process_request(self, request):
        """Store request in local thread.

        WARNING!: Do not set any other data in _thread_locals
        since most probably it won't be updated in other places and
        you will spend weeks to find why software doesn't work.

        Instead of store data in request and write method that
        recovers it from current request.
        """
        _thread_locals.request = request

    def process_response(self, request, response):
        """Clear this from thread after usage"""
        self._clear_request()
        return response

    def process_exception(self, request, exception):
        """We want to remove request from thread locals even for broken
        views. Since we don't return anything - default exception handler
        will work"""
        self._clear_request()


class TimezoneMiddleware(object):
    def process_request(self, request):
        tzname = request.session.get('django_timezone')
        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()
