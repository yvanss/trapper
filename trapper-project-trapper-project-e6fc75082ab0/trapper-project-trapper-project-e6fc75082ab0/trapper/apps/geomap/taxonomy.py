# -*- coding: utf-8 -*-

from trapper.apps.common.taxonomy import BaseTaxonomy


class LocationSettings(BaseTaxonomy):

    MEDIA_EXTENSIONS = [
        '.gpx',
    ]

class DeploymentViewQuality(BaseTaxonomy):
    EXCLUDE = 'Exclude'
    ACCEPTABLE = 'Acceptable'
    GOOD = 'Good'
    PERFECT = 'Perfect'

    CHOICES = (
        (EXCLUDE, 'Exclude'),
        (ACCEPTABLE, 'Acceptable'),
        (GOOD, 'Good'),
        (PERFECT, 'Perfect'),
    )
