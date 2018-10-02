# -*- utf-8 -*-

import os

from django.conf import settings


class SendFileDevServerMiddleware(object):
    """
    Middleware for serving files requested with SendFileResponse.
    Mimics real web server behavior so it should be included at the end
    of MIDDLEWARE_CLASSES.
    WARNING: *Don't even try to use it in production!*
    """
    def process_response(self, request, response):
        """Intercepts """
        if settings.SENDFILE_DEV_SERVER_ENABLED:
            path = response.get(settings.SENDFILE_HEADER)
            if path:
                from django.views.static import serve
                directory = os.path.dirname(path)
                filename = os.path.basename(path)
                content_disposition = response.get('Content-Disposition')
                response = serve(
                    request, path=filename,
                    document_root=settings.PROJECT_ROOT + directory
                )
                if content_disposition:
                    response['Content-Disposition'] = content_disposition
        return response
