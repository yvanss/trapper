# -*- coding: utf-8 -*-
"""Utilities related to encoding/decoding strings and creating hashcodes
that could be used in models with non-integer primary keys"""

import os
import hashlib
import string

__all__ = ['BASE_DICT', 'BASE_LIST', 'base_decode', 'base_encode']


BASE_LIST = string.digits + string.letters
BASE_DICT = dict((c, i) for i, c in enumerate(BASE_LIST))


def base_decode(string_data, reverse_base=BASE_DICT):
    """Decode string data using given list of characters.

    By default list of characters is limited to ascii digits and letters"""
    length = len(reverse_base)
    ret = 0
    for i, c in enumerate(string_data[::-1]):
        try:
            ret += (length ** i) * reverse_base[c]
        except KeyError:
            raise ValueError(u"Character '%s' not in alphabet" % c)
    return ret


def base_encode(integer, base=BASE_LIST):
    """Encode integer value into string value using acceptable list of
    characters."""

    length = len(base)
    ret = ''
    while integer != 0:
        ret = base[integer % length] + ret
        integer /= length
    return ret


def create_hashcode():
    """Creates random base62-encoded integer"""
    return base_encode(
        int(hashlib.md5(os.urandom(24)).hexdigest(), 16)
    )
