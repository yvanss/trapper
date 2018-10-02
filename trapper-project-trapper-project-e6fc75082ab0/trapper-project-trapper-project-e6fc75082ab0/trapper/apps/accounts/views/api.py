# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model

from rest_framework import permissions

from trapper.apps.accounts import serializers as accounts_serializers
from trapper.apps.common.views_api import PaginatedReadOnlyModelViewSet

User = get_user_model()


class UserViewSet(PaginatedReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated, )
    queryset = User.objects.all()
    serializer_class = accounts_serializers.UserSerializer
