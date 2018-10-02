# -*- coding: utf-8 -*-
"""Field definitions and helpers used across project"""

from StringIO import StringIO

#from south.modelsinspector import add_introspection_rules
from taggit.forms import TagField

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import TextField, ImageField
from django.forms import (
    ModelChoiceField, ModelMultipleChoiceField,
    ValidationError, FileField
)
from django.template.defaultfilters import filesizeformat

from trapper.apps.accounts.utils import get_pretty_username
from trapper.apps.common.tools import clean_html

try:
    from PIL import Image
except ImportError:
    import Image


DEFAULT_SIZE = getattr(settings, 'DEFAULT_IMAGE_SIZE', [80, 80])
DEFAULT_COLOR = (255, 255, 255, 0)


class ResizedImageFieldFile(ImageField.attr_class):

    def save(self, name, content, save=True):
        new_content = StringIO()
        content.file.seek(0)
        thumb = Image.open(content.file)
        thumb.thumbnail((
            self.field.max_width,
            self.field.max_height
            ), Image.ANTIALIAS)

        if self.field.use_thumbnail_aspect_ratio:
            img = Image.new(
                "RGBA",
                (self.field.max_width, self.field.max_height),
                self.field.background_color
            )
            img.paste(
                thumb,
                ((self.field.max_width - thumb.size[0]) / 2,
                 (self.field.max_height - thumb.size[1]) / 2)
            )
        else:
            img = thumb

        img.save(new_content, format=thumb.format, **img.info)

        new_content = ContentFile(new_content.getvalue())

        super(ResizedImageFieldFile, self).save(name, new_content, save)


class ResizedImageField(ImageField):
    """This field comes from https://github.com/un1t/django-resized
    application, since repository is not updated for more than 2 years
    and contain only fields it was moved here"""

    attr_class = ResizedImageFieldFile

    def __init__(self, verbose_name=None, name=None, **kwargs):
        self.max_width = kwargs.pop('max_width', DEFAULT_SIZE[0])
        self.max_height = kwargs.pop('max_height', DEFAULT_SIZE[1])
        self.use_thumbnail_aspect_ratio = kwargs.pop(
            u'use_thumbnail_aspect_ratio', False
        )
        self.background_color = kwargs.pop('background_color', DEFAULT_COLOR)
        super(ResizedImageField, self).__init__(verbose_name, name, **kwargs)


class SafeTextField(TextField):
    """Extended version of TextField that clean all html tags and attributes
    that aren't considered as safe before save"""

    def to_python(self, value):
        """
        Before saving to database value should be cleaned
        using :class:`lxml.html.clean.Cleaner`
        """
        return clean_html(value)


class OwnerLabelMixin(object):
    """Simple mixin for prettified version of :class:`auth.User` instances
    in selects"""

    def label_from_instance(self, obj):
        """Use :func:`apps.accounts.utils.get_pretty_username`
        to prettify username"""
        return get_pretty_username(user=obj)


class OwnerModelChoiceField(OwnerLabelMixin, ModelChoiceField):
    """Choice field with prettified version of username that should be used
    for ModelChoiceField"""
    pass


class OwnerModelMultipleChoiceField(OwnerLabelMixin, ModelMultipleChoiceField):
    """Choice field with prettified version of username that should be used
    for ModelMultipleChoiceField"""
    pass


class SimpleTagField(TagField):
    def clean(self, value):
        value = super(TagField, self).clean(value)
        try:
            return value.split(',')
        except ValueError:
            raise ValidationError(
                'Please provide a comma-separated list of tags.'
            )


#http://chriskief.com/2013/10/19/limiting-upload-file-size-with-django-forms/
class RestrictedFileField(FileField):
    def __init__(self, *args, **kwargs):
        self.file_types = kwargs.pop('file_types', None)
        self.max_upload_size = kwargs.pop('max_upload_size', None)
        if not self.max_upload_size:
            self.max_upload_size = settings.MAX_UPLOAD_SIZE
        if not self.file_types:
            self.file_types = settings.ALLOWED_FILE_TYPES
        super(RestrictedFileField, self).__init__(*args, **kwargs)
            
    def clean(self, *args, **kwargs):
        data = super(RestrictedFileField, self).clean(*args, **kwargs)
        try:
            if data.content_type.split('/')[1] in self.file_types:
                if data.size > self.max_upload_size:
                    raise ValidationError(
                        u'File size must be under {max}. Current file size is {current}.'.format(
                            max=filesizeformat(self.max_upload_size), 
                            current=filesizeformat(data.size)
                        )
                    )
            else:
                raise ValidationError(
                    'File type {ftype} is not supported.'.format(
                        ftype=data.content_type
                    )
                )
        except AttributeError:
            pass
        return data


#add_introspection_rules(
#    [], [r"^trapper\.apps\.common\.fields\.ResizedImageField"]
#)
#add_introspection_rules(
#    [], [r"^trapper\.apps\.common\.fields\.SafeTextField"]
#)
