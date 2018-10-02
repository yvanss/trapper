# -*- coding: utf-8 -*-

from django.contrib.auth.views import redirect_to_login
from django.views.generic import View
from django.http import Http404, HttpResponseForbidden

from trapper.apps.sendfile.response import SendFileResponse


class BaseServeFileView(View):
    """Base class for serving files through x-sendfile

    By default only GET method is allowed

    authenticated_only - flag determine if non-authenticated users should have
        access to file.
        False by default

    response_handler - handler that will be used to serve file
        SendFileResponse by default
    """
    http_method_names = ['get']
    authenticated_only = False
    partner_only = False
    raise_exception = False
    response_handler = SendFileResponse

    def check_access_rights(self, request, *args, **kwargs):
        """Based on authenticated_only flag redirect unauthenticated users
        to login page or give them access to file"""
        response = None
        if self.authenticated_only and not request.user.is_authenticated():
            if self.raise_exception:
                response = HttpResponseForbidden()
            else:
                response = redirect_to_login(next=request.get_full_path())
        return response

    def dispatch(self, request, *args, **kwargs):
        """
        Perform checking for access rights before serving file
        """
        response = self.check_access_rights(request, *args, **kwargs)
        if response is not None:
            return response
        return super(BaseServeFileView, self).dispatch(
            request, *args, **kwargs
        )

    def serve_file(self, *args, **kwargs):
        """Prepare sendfile headers"""
        return self.response_handler(*args, **kwargs)


class DirectServeFileView(BaseServeFileView):
    def check_access_rights(self, request, *args, **kwargs):
        """Direct download is available only for staff or superusers.
        All other people with get standard Access Denied page"""
        response = None
        if not(request.user.is_staff or request.user.is_superuser):
            response = HttpResponseForbidden()
        return response

    def get(self, request):
        file_name = request.GET.get('file', None)

        if file_name is None:
            raise Http404
        else:
            return self.serve_file(file_name)

view_direct_serve_file = DirectServeFileView.as_view()
