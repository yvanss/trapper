# -*- coding: utf-8 -*-
"""Base serializer classes used in other applications where REST API is
defined"""

from rest_framework import serializers

from trapper.apps.accounts.utils import get_pretty_username


class BaseListSerializer(serializers.ListSerializer):
    """Base list serializer class."""

    def __init__(self, *args, **kwargs):
        super(BaseListSerializer, self).__init__(*args, **kwargs)
        self.user = self.context['request'].user


class BasePKSerializer(serializers.ModelSerializer):
    """Base serializer class. Contains read-only `pk` field."""

    pk = serializers.ReadOnlyField()  # Read-only value of primary key


class PrettyUserField(serializers.ReadOnlyField):
    """This field takes user instance as value and return
    pretty formatted name"""

    def to_representation(self, obj):
        return get_pretty_username(obj)
