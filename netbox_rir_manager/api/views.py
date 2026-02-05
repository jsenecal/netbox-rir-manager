from netbox.api.viewsets import NetBoxModelViewSet

from netbox_rir_manager.api.serializers import (
    RIRConfigSerializer,
    RIRContactSerializer,
    RIRNetworkSerializer,
    RIROrganizationSerializer,
    RIRSyncLogSerializer,
    RIRUserKeySerializer,
)
from netbox_rir_manager.filtersets import (
    RIRConfigFilterSet,
    RIRContactFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSyncLogFilterSet,
    RIRUserKeyFilterSet,
)
from netbox_rir_manager.models import RIRConfig, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog, RIRUserKey


class RIRConfigViewSet(NetBoxModelViewSet):
    queryset = RIRConfig.objects.prefetch_related("tags")
    serializer_class = RIRConfigSerializer
    filterset_class = RIRConfigFilterSet


class RIROrganizationViewSet(NetBoxModelViewSet):
    queryset = RIROrganization.objects.prefetch_related("tags")
    serializer_class = RIROrganizationSerializer
    filterset_class = RIROrganizationFilterSet


class RIRContactViewSet(NetBoxModelViewSet):
    queryset = RIRContact.objects.prefetch_related("tags")
    serializer_class = RIRContactSerializer
    filterset_class = RIRContactFilterSet


class RIRNetworkViewSet(NetBoxModelViewSet):
    queryset = RIRNetwork.objects.prefetch_related("tags")
    serializer_class = RIRNetworkSerializer
    filterset_class = RIRNetworkFilterSet


class RIRSyncLogViewSet(NetBoxModelViewSet):
    queryset = RIRSyncLog.objects.prefetch_related("tags")
    serializer_class = RIRSyncLogSerializer
    filterset_class = RIRSyncLogFilterSet


class RIRUserKeyViewSet(NetBoxModelViewSet):
    queryset = RIRUserKey.objects.prefetch_related("tags")
    serializer_class = RIRUserKeySerializer
    filterset_class = RIRUserKeyFilterSet
