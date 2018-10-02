# -*- coding: utf-8 -*-
"""Various functions that could be used in other applications models"""
import os


def delete_old_file(instance, field):
    """Check if file for given field has been changed, and
    if yes then delete old file"""
    if instance.pk:
        try:
            old_instance = instance.__class__.objects.get(pk=instance.pk)
        except instance.__class__.DoesNotExist:
            # Some celery async tasks can throw errors here
            pass
        else:
            old_file = getattr(old_instance, field)
            new_file = getattr(instance, field)

            if (
                old_file and
                old_file != new_file and
                os.path.exists(old_file.path)
            ):
                os.remove(old_file.path)

