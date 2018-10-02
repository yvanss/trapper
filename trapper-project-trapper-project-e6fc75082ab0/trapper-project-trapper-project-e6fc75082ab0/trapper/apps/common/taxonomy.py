# -*- coding: utf-8 -*-

__all__ = ['BaseTaxonomy']


class BaseTaxonomy(object):
    """Base taxonomy mixin which is commonly used for model choices."""
    CHOICES = ()
    ALL_CHOICE = ('', 'All')

    @classmethod
    def get_all_choices(cls, base_choices=None):
        """Helper method which adds ALL choice option to defined ones"""
        choices = base_choices or cls.CHOICES
        return (cls.ALL_CHOICE,) + choices

    @classmethod
    def get_filter_choices(cls, base_choices=None):
        """Helper method that add ALL option to given ones.
        This method is used commonly in filters when only **values** are used
        """
        choices = (cls.ALL_CHOICE, )
        choices += base_choices or cls.CHOICES
        return [(val, val) for key, val in choices]

    @classmethod
    def choices_as_dict(cls):
        """Convert defined choices into dictionary"""
        return dict(cls.CHOICES)
