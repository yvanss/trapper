from django import template
from django.conf import settings


register = template.Library()


@register.inclusion_tag('geomap/tags/css.html')
def geomap_leaflet_storage_css():
    return {
        "STATIC_URL": settings.STATIC_URL
    }


@register.inclusion_tag('geomap/tags/js.html')
def geomap_leaflet_storage_js(locale=None):
    return {
        "STATIC_URL": settings.STATIC_URL,
        "locale": locale
    }
