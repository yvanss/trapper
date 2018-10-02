# -*- coding: utf-8 -*-

from trapper.middleware import get_current_user
from trapper.apps.common.taxonomy import BaseTaxonomy


class ResourceMimeType(BaseTaxonomy):
    """Mimetypes handled by :class:`storage.Resource`"""
    AUDIO_OGG = 'audio/ogg'
    AUDIO_MP3 = 'audio/mp3'
    AUDIO_XWAV = 'audio/x-wav'
    AUDIO_WAV = 'audio/wav'
    VIDEO_MP4 = 'video/mp4'
    VIDEO_WEBM = 'video/webm'
    VIDEO_OGG = 'video/ogg'
    IMAGE_JPEG = 'image/jpeg'

    CHOICES = (
        (AUDIO_OGG, 'audio/ogg'),
        (AUDIO_MP3, 'audio/mp3'),
        (AUDIO_XWAV, 'audio/x-wav'),
        (AUDIO_WAV, 'audio/wav'),
        (VIDEO_MP4, 'video/mp4'),
        (VIDEO_WEBM, 'video/webm'),
        (VIDEO_OGG, 'video/ogg'),
        (IMAGE_JPEG, 'image/jpeg'),
    )

    MEDIA_EXTENSIONS = [
        '.ogg', '.mp3', '.wav', '.mp4', '.webm', '.ogg', '.jpeg', '.jpg'
    ]


class ResourceType(BaseTaxonomy):
    """Resource types handled by :class:`storage.Resource`"""
    TYPE_VIDEO = "V"
    TYPE_IMAGE = "I"
    TYPE_AUDIO = "A"

    THUMBNAIL_TYPES = (TYPE_VIDEO, TYPE_IMAGE)

    CHOICES = (
        (TYPE_VIDEO, 'Video'),
        (TYPE_IMAGE, 'Image'),
        (TYPE_AUDIO, 'Audio'),
    )


class ResourceStatus(BaseTaxonomy):
    """Share statuses handled by :class:`storage.Resource`"""
    PRIVATE = 'Private'
    ON_DEMAND = 'OnDemand'
    PUBLIC = 'Public'

    CHOICES = (
        (PRIVATE, 'Private'),
        (ON_DEMAND, 'On demand'),
        (PUBLIC, 'Public'),
    )


class CollectionStatus(BaseTaxonomy):
    """Share statuses handled by :class:`storage.Collection`"""
    PRIVATE = 'Private'
    ON_DEMAND = 'OnDemand'
    PUBLIC = 'Public'

    CHOICES = (
        (PRIVATE, 'Private'),
        (ON_DEMAND, 'On demand'),
        (PUBLIC, 'Public'),
    )


class CollectionManagers(BaseTaxonomy):
    """Container for manager/owner choices excluding currently logged user"""
    @classmethod
    def get_all_choices(cls, base_choices=None):
        if base_choices:
            user = get_current_user()
            if user and user.is_authenticated():
                base_choices = base_choices.exclude(pk=user.pk)
            choices = tuple(base_choices.values_list('pk', 'username'))
        else:
            choices = super(CollectionManagers, cls).get_all_choices()
        return (cls.ALL_CHOICE,) + choices


class CollectionProjects(BaseTaxonomy):
    """Container for choices for collection projects"""
    pass


class CollectionMemberLevels(BaseTaxonomy):
    """Roles used by :class:`storage.CollectionMember`"""
    ACCESS = 1
    UPDATE = 2
    CREATE = 3
    DELETE = 4
    ACCESS_REQUEST = 5
    ACCESS_BASIC = 6

    ANY = (
        ACCESS, UPDATE, CREATE, DELETE, ACCESS_REQUEST,
        ACCESS_BASIC
    )

    CHOICES = (
        (ACCESS, 'Can view'),
        (UPDATE, 'Can update'),
        (CREATE, 'Can create'),
        (DELETE, 'Can delete'),
        (ACCESS_REQUEST, 'Can view (request)'),
        (ACCESS_BASIC, 'Can view (basic)'),
    )

    CHOICES_DICT = dict(CHOICES)


class CollectionSettings(BaseTaxonomy):

    MEDIA_EXTENSIONS = [
        '.zip',
    ]
