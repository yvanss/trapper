# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model

from rest_framework import serializers

from trapper.apps.common.serializers import BasePKSerializer
from trapper.apps.accounts.utils import get_pretty_username


class UserSerializer(BasePKSerializer):

    class Meta:
        model = get_user_model()
        fields = (
            'pk', 'username', 'first_name', 'last_name', 'email',
            'name'
        )
    name = serializers.SerializerMethodField()

    def get_name(self, item):
        """Custom method for retrieving prettified username"""
        return get_pretty_username(user=item)
