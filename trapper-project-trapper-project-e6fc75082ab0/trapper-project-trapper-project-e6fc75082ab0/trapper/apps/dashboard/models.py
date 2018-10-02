# -*- coding: utf-8 -*

from django.db import models

from django.template.defaultfilters import slugify


class DashboardButton(models.Model):
    name = models.CharField(u'Name', max_length=30)
    href = models.SlugField(u'Slug', editable=False, blank=True, null=True)
    url = models.CharField(
        u'External URL', blank=True, null=True, max_length=50
    )
    css_class = models.CharField(
        u'Fontawesome class', blank=True, null=True,
        help_text=u'http://fortawesome.github.io/Font-Awesome/icons/',
        max_length=20
    )

    def save(self, *args, **kwargs):
        if not self.pk:
            super(DashboardButton, self).save(*args, **kwargs)

        if not self.url:
            self.href = slugify(unicode(self.name))

        super(DashboardButton, self).save(*args, **kwargs)
