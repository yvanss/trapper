# -*- coding: utf-8 -*-


class MessageType(object):
    """
    Contain all variables used to define message type.
    """
    STANDARD = 1
    RESOURCE_REQUEST = 2
    COLLECTION_REQUEST = 3
    RESOURCE_DELETED = 4
    COLLECTION_DELETED = 5
    RESEARCH_PROJECT_CREATED = 6

    CHOICES = (
        (STANDARD, u"Standard message"),
        (RESOURCE_REQUEST, u"Resource request"),
        (COLLECTION_REQUEST, u"Collection request"),
        (RESOURCE_DELETED, u'Resource deleted'),
        (COLLECTION_DELETED, u'Collection deleted'),
        (RESEARCH_PROJECT_CREATED, u'Research project created')
    )

    DICT_CHOICES = dict(CHOICES)

class MessageApproveStatus(object):
    APPROVED = True
    DECLINED = False
    UNKNOWN = None

    CHOICES = (
        (APPROVED, u"Approved"),
        (DECLINED, u'Declined'),
        (UNKNOWN, u'Not processed yet')
    )
