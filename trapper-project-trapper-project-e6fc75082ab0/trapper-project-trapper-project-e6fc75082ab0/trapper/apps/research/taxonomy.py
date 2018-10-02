# -*- coding: utf-8 -*-

from trapper.apps.common.taxonomy import BaseTaxonomy

__all__ = ['ResearchProjectRoleType']


class ResearchProjectRoleType(BaseTaxonomy):
    ADMIN = 1
    EXPERT = 2
    COLLABORATOR = 3

    ANY = (ADMIN, EXPERT, COLLABORATOR, )
    EDIT = (ADMIN, )
    DELETE = (ADMIN,)

    CHOICES = (
        (ADMIN, "Admin"),
        (EXPERT, "Expert"),
        (COLLABORATOR, "Collaborator"),
    )


class ResearchProjectStatus(BaseTaxonomy):
    APPROVED = True
    REJECTED = False
    NOT_PROCESSED = None

    CHOICES = (
        (NOT_PROCESSED, 'Not yet processed'),
        (REJECTED, 'Rejected'),
        (APPROVED, 'Approved'),
    )


class ResearchProjectCollectionChoices(BaseTaxonomy):
    pass
