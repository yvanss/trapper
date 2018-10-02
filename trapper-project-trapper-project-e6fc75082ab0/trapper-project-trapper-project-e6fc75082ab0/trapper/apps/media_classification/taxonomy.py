
# -*- encoding: utf-8 -*-

from django import forms
from trapper.apps.media_classification.widgets import VideoTimeRangeField
from trapper.apps.common.taxonomy import BaseTaxonomy


class ClassificatorSettings(BaseTaxonomy):

    FIELDS = {
        'B': forms.BooleanField,
        'F': forms.FloatField,
        'I': forms.IntegerField,
        'S': forms.CharField,
    }
    FIELD_BOOLEAN = 'B'
    FIELD_INTEGER = 'I'
    FIELD_FLOAT = 'F'
    FIELD_STRING = 'S'

    FIELD_LABELS = {
        FIELD_BOOLEAN: 'Bool',
        FIELD_FLOAT: 'Float',
        FIELD_INTEGER: 'Integer',
        FIELD_STRING: 'String'
    }

    NUMERIC_MAPPERS = {
        'F': float,
        'I': int
    }

    FIELD_CHOICES = FIELD_LABELS.items()

    TARGET_STATIC = 'S'
    TARGET_DYNAMIC = 'D'
    TARGETS = {
        TARGET_STATIC: 'Static',
        TARGET_DYNAMIC: 'Dynamic',
    }

    TARGET_CHOICES = TARGETS.items()

    PREDEFINED_ATTRIBUTES_SIMPLE = {
        'annotations': {
            'label': 'Annotations',
            'help_text': (
                'Use annotations to classify precisly partial contents of '
                'your media files (at the moment available only for videos)'
            ),
            'formfield': VideoTimeRangeField,
        },
        'comments': {
            'label': 'Comments',
            'help_text': 'Simple Comments Field (TextArea)',
            'formfield': forms.CharField,
            'widget': forms.Textarea(attrs={'cols': 10, 'rows': 3}),
        },
    }

    # predefined, model-based attributes configuration
    PREDEFINED_ATTRIBUTES_MODELS = {
        'species': {
            'app': 'extra_tables',
            'label': 'Species',
            'choices_labels': 'english_name',
            'search_fields': [
                'english_name__icontains', 'latin_name__icontains'
            ],
            'filters': ['family', 'genus'],
            },
        }

    PREDEFINED_NAMES = (
        PREDEFINED_ATTRIBUTES_SIMPLE.keys() +
        PREDEFINED_ATTRIBUTES_MODELS.keys()
    )

    TEMPLATE_TAB = 'tab'
    TEMPLATE_INLINE = 'inline'

    TEMPLATE_CHOICES = (
        (TEMPLATE_INLINE, 'Inline'),
        (TEMPLATE_TAB, 'Tabbed')
    )


class ClassificationProjectRoleLevels(BaseTaxonomy):
    ADMIN = 1
    EXPERT = 2
    COLLABORATOR = 3

    ANY = (ADMIN, EXPERT, COLLABORATOR, )
    UPDATE = (ADMIN,)
    DELETE = (ADMIN,)
    VIEW_CLASSIFICATIONS = (ADMIN, COLLABORATOR)
    VIEW_USER_CLASSIFICATIONS = (ADMIN,)

    CHOICES = (
        (ADMIN, "Admin"),
        (EXPERT, "Expert"),
        (COLLABORATOR, "Collaborator"),
    )

    SEQUENCE_CHOICES = (
        (EXPERT, "Expert"),
    )


class ClassificationProjectStatus(BaseTaxonomy):
    ONGOING = 1
    FINISHED = 2

    CHOICES = (
        (ONGOING, 'Ongoing'),
        (FINISHED, 'Finished'),
    )


class ClassificationStatus(BaseTaxonomy):
    APPROVED = True
    REJECTED = False

    CHOICES = (
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    )

    CHOICES_DICT = dict(CHOICES)

class ClassifyMessages(object):
    MSG_CLASSIFICATOR_MISSING = (
        u'You can not classify records without a classificator assigned to a project.'
    )

    MSG_PERMS_REQUIRED = (
        u'You have to be a project admin to run this action.'
    )

    MSG_CLASSIFY_MULTIPLE_FAILED = (
        u"Unable to classify multiple resources. Please try again."
    )

    MSG_CLASSIFY_ERRORS = u"Your classification form contains errors."

    MSG_APPROVE_PERMS = (
        u"You have no permission to approve selected classification(s). The admin role is "
        u"required."
    )

    MSG_IS_APPROVED = u'This classification is already approved.'

    MSG_CLASSIFICATION_MISSING = u'There is no such a classification.'

    MSG_SUCCESS = u'Your classification(s) has been successfully saved in a database.'
    MSG_SUCCESS_APPROVED = u'You have successfully approved selected classification(s).'
