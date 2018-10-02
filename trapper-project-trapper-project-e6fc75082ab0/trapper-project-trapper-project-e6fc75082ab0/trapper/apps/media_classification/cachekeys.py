# -*- coding:utf-8 -*-


def get_form_fields_cache_name(classificator):
    """Cache name used for caching generated classificator form"""
    base_name = 'classificator:form_fields:{pk}'
    return base_name.format(pk=classificator.pk)
