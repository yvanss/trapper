# -*- coding utf-8 -*-


import mimetypes

from django.conf import settings
from django import http
from django.utils.encoding import smart_str


class SendFileResponse(http.HttpResponse):
    """HTTP Response for serving media using x-sendfile logic"""

    def __init__(self, filename, mimetype=None, encoding=None, root=None):
        super(SendFileResponse, self).__init__()
        self.filename = filename
        self.mimetype = mimetype
        self.encoding = encoding
        self.root = root or settings.SENDFILE_ROOT
        self.path = self.get_absolute_path()
        self.set_sendfile_headers()

    def get_absolute_path(self):
        """Generates absolute path to file"""
        return unicode(self.root + self.filename).replace('//', '/')

    def get_sendfile_header(self):
        """Generates value for SENDFILE_HEADER"""
        return smart_str(unicode(self.path))

    def get_content_type_and_encoding(self):
        """Generates values for Content-Type and Content-Encoding headers"""
        guessed_mimetype, guessed_encoding = mimetypes.guess_type(self.filename)
        if self.mimetype:
            content_type = self.mimetype
        else:
            if guessed_mimetype:
                content_type = guessed_mimetype
            else:
                content_type = 'application/octet-stream'
        if self.encoding:
            encoding = self.encoding
        else:
            encoding = guessed_encoding
        return content_type, encoding

    def set_sendfile_headers(self):
        """
        Updates HTTP headers according to file options provided in __init__
        """
        content_type, encoding = self.get_content_type_and_encoding()
        self._set_header('Content-Type', content_type)
        self._set_header('Content-Encoding', encoding)

        sendfile_header = self.get_sendfile_header()
        self._set_header(settings.SENDFILE_HEADER, sendfile_header)

    def _set_header(self, name, value):
        """Utility for setting header values with file metadata."""
        if value is None:
            del self[name]
        else:
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            self[name] = value
