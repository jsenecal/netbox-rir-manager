from core.api.serializers import JobSerializer
from netbox.api.viewsets import NetBoxModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from netbox_rir_manager.api.serializers import (
    NetworkReallocateSerializer,
    NetworkReassignSerializer,
    RIRAddressSerializer,
    RIRConfigSerializer,
    RIRContactSerializer,
    RIRCustomerSerializer,
    RIRNetworkSerializer,
    RIROrganizationSerializer,
    RIRSyncLogSerializer,
    RIRTicketSerializer,
    RIRUserKeySerializer,
)
from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.constants import NO_API_KEY_MESSAGE
from netbox_rir_manager.filtersets import (
    RIRAddressFilterSet,
    RIRConfigFilterSet,
    RIRContactFilterSet,
    RIRCustomerFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSyncLogFilterSet,
    RIRTicketFilterSet,
    RIRUserKeyFilterSet,
)
from netbox_rir_manager.jobs import SyncRIRConfigJob
from netbox_rir_manager.models import (
    RIRAddress,
    RIRConfig,
    RIRContact,
    RIRCustomer,
    RIRNetwork,
    RIROrganization,
    RIRSyncLog,
    RIRTicket,
    RIRUserKey,
)
from netbox_rir_manager.services.arin_results import ARINDataError, ARINWriteError
from netbox_rir_manager.services.net_writes import (
    reallocation_request,
    submit_net_delete,
    submit_net_remove,
    submit_reallocation,
)
from netbox_rir_manager.services.reassignment import reassignment_request, submit_reassignment


def arin_outcome_response(request, outcome):
    """The response to a write ARIN accepted.

    With a ticket: 201 and the serialized ticket, as before. Without one (ARIN processed the
    write immediately, or NetBox could not record it): 200 and
    {"detail", "recorded", "ticket": null, "net"}, where net is the linked child network or null.
    """
    if outcome.ticket is not None:
        return Response(
            RIRTicketSerializer(outcome.ticket, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
    net = RIRNetworkSerializer(outcome.net, context={"request": request}).data if outcome.net else None
    return Response(
        {"detail": outcome.message, "recorded": outcome.recorded, "ticket": None, "net": net},
        status=status.HTTP_200_OK,
    )


class RIRConfigViewSet(NetBoxModelViewSet):
    queryset = RIRConfig.objects.prefetch_related("tags")
    serializer_class = RIRConfigSerializer
    filterset_class = RIRConfigFilterSet

    @action(detail=True, methods=["post"], url_path="sync")
    def sync(self, request, pk=None):
        """Queue a background sync of this config, run with the requesting user's own key.

        Answers 202 with the queued core Job so a caller can poll /api/core/jobs/<id>/ for the outcome.
        """
        rir_config = self.get_object()
        if not rir_config.resolve_key(request.user):
            return Response(
                {"detail": NO_API_KEY_MESSAGE},
                status=status.HTTP_403_FORBIDDEN,
            )

        job = SyncRIRConfigJob.enqueue(instance=rir_config, user=request.user)
        return Response(
            JobSerializer(job, context={"request": request}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class RIROrganizationViewSet(NetBoxModelViewSet):
    queryset = RIROrganization.objects.prefetch_related("tags")
    serializer_class = RIROrganizationSerializer
    filterset_class = RIROrganizationFilterSet


class RIRContactViewSet(NetBoxModelViewSet):
    queryset = RIRContact.objects.prefetch_related("tags")
    serializer_class = RIRContactSerializer
    filterset_class = RIRContactFilterSet


class RIRCustomerViewSet(NetBoxModelViewSet):
    queryset = RIRCustomer.objects.prefetch_related("tags")
    serializer_class = RIRCustomerSerializer
    filterset_class = RIRCustomerFilterSet


class RIRNetworkViewSet(NetBoxModelViewSet):
    queryset = RIRNetwork.objects.prefetch_related("tags")
    serializer_class = RIRNetworkSerializer
    filterset_class = RIRNetworkFilterSet

    @action(detail=True, methods=["post"], url_path="reassign")
    def reassign(self, request, pk=None):
        network = self.get_object()
        serializer = NetworkReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            return Response(
                {"detail": NO_API_KEY_MESSAGE},
                status=status.HTTP_403_FORBIDDEN,
            )

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        net, customer, org_handle = reassignment_request(serializer.validated_data)
        try:
            outcome = submit_reassignment(backend, network, user_key, net, customer=customer, org_handle=org_handle)
        except ARINDataError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ARINWriteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return arin_outcome_response(request, outcome)

    @action(detail=True, methods=["post"], url_path="reallocate")
    def reallocate(self, request, pk=None):
        network = self.get_object()
        serializer = NetworkReallocateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            return Response(
                {"detail": NO_API_KEY_MESSAGE},
                status=status.HTTP_403_FORBIDDEN,
            )

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        net = reallocation_request(serializer.validated_data)
        try:
            outcome = submit_reallocation(backend, network, user_key, net)
        except ARINDataError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ARINWriteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return arin_outcome_response(request, outcome)

    @action(detail=True, methods=["post"], url_path="remove")
    def remove_net(self, request, pk=None):
        network = self.get_object()
        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            return Response(
                {"detail": NO_API_KEY_MESSAGE},
                status=status.HTTP_403_FORBIDDEN,
            )

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        try:
            submit_net_remove(backend, network)
        except ARINWriteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"detail": f"Network {network.handle} removed."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="delete-arin")
    def delete_arin(self, request, pk=None):
        network = self.get_object()
        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            return Response(
                {"detail": NO_API_KEY_MESSAGE},
                status=status.HTTP_403_FORBIDDEN,
            )

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        try:
            outcome = submit_net_delete(backend, network, user_key)
        except ARINWriteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return arin_outcome_response(request, outcome)


class RIRAddressViewSet(NetBoxModelViewSet):
    queryset = RIRAddress.objects.prefetch_related("tags")
    serializer_class = RIRAddressSerializer
    filterset_class = RIRAddressFilterSet


class RIRSyncLogViewSet(NetBoxModelViewSet):
    queryset = RIRSyncLog.objects.prefetch_related("tags")
    serializer_class = RIRSyncLogSerializer
    filterset_class = RIRSyncLogFilterSet


class RIRTicketViewSet(NetBoxModelViewSet):
    queryset = RIRTicket.objects.prefetch_related("tags")
    serializer_class = RIRTicketSerializer
    filterset_class = RIRTicketFilterSet

    @action(detail=True, methods=["post"], url_path="refresh")
    def refresh(self, request, pk=None):
        """Refresh ticket status from ARIN - placeholder for future implementation."""
        ticket = self.get_object()
        # For now, return current ticket data.
        # Full ARIN ticket status check would require a ticket lookup API method.
        return Response(
            RIRTicketSerializer(ticket, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class RIRUserKeyViewSet(NetBoxModelViewSet):
    queryset = RIRUserKey.objects.prefetch_related("tags")
    serializer_class = RIRUserKeySerializer
    filterset_class = RIRUserKeyFilterSet
