# -*- coding: utf-8 -*-

from django.db import models


class Species(models.Model):
    latin_name = models.CharField(max_length=100, blank=False)
    english_name = models.CharField(max_length=100, blank=False)
    family = models.CharField(max_length=100, blank=True)
    genus = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['english_name']

    def __unicode__(self):
        return unicode('%s : %s') % (self.english_name, self.latin_name)
