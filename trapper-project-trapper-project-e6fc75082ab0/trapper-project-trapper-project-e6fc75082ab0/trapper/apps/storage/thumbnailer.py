# -*- coding: utf-8 -*-
"""
Module that holds logic for generting thumbnails from either images
or videos.

For videos by default thumbnail is generated from 5th second.
Thumbnailer construction supports using it as celery task.
"""

import os

from cStringIO import StringIO
from PIL import Image
import subprocess

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from trapper.apps.storage.taxonomy import ResourceType

__all__ = ['Thumbnailer', 'ThumbnailerException']


class ThumbnailerException(Exception):
    """Default exception used by thumbnailer that could be
    easily catch at other modules"""
    pass


class Thumbnailer(object):
    """Thumbnailer class for converting images/videos"""
    FFMPEG_FRAME_TIME = '00:00:01'
    FFMPEG_FRAME_TIME = getattr(settings, 'FFMPEG_FRAME_TIME', FFMPEG_FRAME_TIME)

    def __init__(self, resource):
        """Thumbnailer requires :class:`storage.Resource` instance

        @:param resource: :class:`storage.Resource` model instance
        """
        self.resource = resource

    def create(self):
        """Detect what processor should be used to generate thumbnails and
        run it. If there is no processor that could handle resource,
        throw exception"""
        resource_processor = self.processor
        if callable(resource_processor):
            resource_processor()
        else:
            raise ThumbnailerException(u"This resource type is not handled")

    def prepare_thumbnail(self, raw_image, extension):
        """Convert raw thumbnail image into :class:`models.ImageField`
        For that process image is converted using PIL and written into StringIO

        @:param raw_image - image file content
        @:param extension - extension of file
        """
        try:
            buff = StringIO(raw_image)
            img = Image.open(buff)
            img.thumbnail(settings.DEFAULT_THUMBNAIL_SIZE, Image.ANTIALIAS)
            temp_handle = StringIO()
            img.save(temp_handle, extension, quality=60)
            buff.close()
        except IOError:
            return 1

        temp_handle.seek(0)

        suf = SimpleUploadedFile(
            os.path.split(self.resource.file.name)[-1],
            temp_handle.read(), content_type=extension
        )
        temp_handle.close()
        self.resource.file_thumbnail.save(
            '{path}_thumbnail.{ext}'.format(
                path=os.path.splitext(suf.name)[0],
                ext=extension
            ),
            suf, save=True
        )

    def prepare_preview(self, raw_image, extension):
        """Convert raw thumbnail image into :class:`models.ImageField`
        For that process image is converted using PIL and written into StringIO

        @:param raw_image - image file content
        @:param extension - extension of file
        """
        try:
            buff = StringIO(raw_image)
            img = Image.open(buff)
            img.thumbnail(settings.DEFAULT_PREVIEW_SIZE, Image.ANTIALIAS)
            temp_handle = StringIO()
            img.save(temp_handle, extension, quality=60)
            buff.close()
        except IOError:
            return 1
        temp_handle.seek(0)
        suf = SimpleUploadedFile(
            os.path.split(self.resource.file.name)[-1],
            temp_handle.read(), content_type=extension
        )
        temp_handle.close()
        self.resource.file_preview.save(
            '{path}_preview.{ext}'.format(
                path=os.path.splitext(suf.name)[0],
                ext=extension
            ),
            suf, save=True
        )

    def process_image(self):
        """Processor used to prepare thumbnail from images.
        """
        mime_type = self.resource.mime_type
        extension = mime_type.split('/')[-1]
        self.resource.file.seek(0)
        raw_image = self.resource.file.read()
        self.prepare_thumbnail(raw_image=raw_image, extension=extension)
        self.prepare_preview(raw_image=raw_image, extension=extension)

    def process_video(self):
        """Processor used to prepare thumbnail from videos.
        This processor uses ffmpeg library
        """
        if settings.VIDEO_THUMBNAIL_ENABLED:
            cmd = [
                'ffmpeg',
                '-ss',
                self.FFMPEG_FRAME_TIME,
                '-i',
                self.resource.file.path,
                '-frames',
                ' 1',
                '-f',
                'image2',
                '-'
            ]
            extension = 'jpeg'
            raw_image = subprocess.check_output(cmd)
            self.prepare_thumbnail(raw_image=raw_image, extension=extension)

    @property
    def processor(self):
        """Property that return processor that should be used to work with
        given resource"""
        processor_map = {
            ResourceType.TYPE_IMAGE: self.process_image,
            ResourceType.TYPE_VIDEO: self.process_video,
        }
        return processor_map.get(self.resource.resource_type, None)
