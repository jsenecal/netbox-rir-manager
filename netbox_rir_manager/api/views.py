from netbox.api.viewsets import NetBoxModelViewSet

from netbox_rir_manager.api.serializers import (
    RIRAccountSerializer,
    RIRContactSerializer,
    RIRNetworkSerializer,
    RIROrganizationSerializer,
    RIRSyncLogSerializer,
)
from netbox_rir_manager.filtersets import (
    RIRAccountFilterSet,
    RIRContactFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSyncLogFilterSet,
)
from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog


class RIRAccountViewSet(NetBoxModelViewSet):
    queryset = RIRAccount.objects.prefetch_related("tags")
    serializer_class = RIRAccountSerializer
    filterset_class = RIRAccountFilterSet


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
