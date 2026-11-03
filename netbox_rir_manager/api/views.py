from core.api.serializers import JobSerializer
from django.utils import timezone
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
from netbox_rir_manager.choices import normalize_ticket_status
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
from netbox_rir_manager.services.reassignment import ReassignmentError, reassignment_request, submit_reassignment


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
            ticket = submit_reassignment(backend, network, user_key, net, customer=customer, org_handle=org_handle)
        except ReassignmentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            RIRTicketSerializer(ticket, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

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
        data = serializer.validated_data
        net_data = {
            "org_handle": data["org_handle"],
            "net_name": data.get("net_name", ""),
            "start_address": str(data["start_address"]),
            "end_address": str(data["end_address"]),
        }
        result = backend.reallocate_network(network.handle, net_data)
        if result is None:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config,
                operation="reallocate",
                object_type="network",
                object_handle=network.handle,
                status="error",
                message="Reallocation failed",
            )
            return Response(
                {"detail": "Reallocation failed at ARIN."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        ticket = RIRTicket.objects.create(
            rir_config=network.rir_config,
            ticket_number=result.get("ticket_number", ""),
            ticket_type=result.get("ticket_type", "IPV4_REALLOCATE"),
            status=normalize_ticket_status(result.get("ticket_status", "")),
            network=network,
            submitted_by=user_key,
            created_date=timezone.now(),
            raw_data=result.get("raw_data", {}),
        )
        RIRSyncLog.objects.create(
            rir_config=network.rir_config,
            operation="reallocate",
            object_type="network",
            object_handle=network.handle,
            status="success",
            message=f"Reallocation submitted, ticket {ticket.ticket_number}",
        )
        return Response(
            RIRTicketSerializer(ticket, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

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
        success = backend.remove_network(network.handle)
        if success:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config,
                operation="remove",
                object_type="network",
                object_handle=network.handle,
                status="success",
                message=f"Removed network {network.handle} from ARIN",
            )
            return Response(
                {"detail": f"Network {network.handle} removed."},
                status=status.HTTP_200_OK,
            )
        else:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config,
                operation="remove",
                object_type="network",
                object_handle=network.handle,
                status="error",
                message="Failed to remove network from ARIN",
            )
            return Response(
                {"detail": "Failed to remove network from ARIN."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

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
        result = backend.delete_network(network.handle)
        if result is None:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config,
                operation="delete",
                object_type="network",
                object_handle=network.handle,
                status="error",
                message="Failed to delete network at ARIN",
            )
            return Response(
                {"detail": "Failed to delete network at ARIN."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        ticket = RIRTicket.objects.create(
            rir_config=network.rir_config,
            ticket_number=result.get("ticket_number", ""),
            ticket_type="NET_DELETE_REQUEST",
            status=normalize_ticket_status(result.get("ticket_status", "")),
            network=network,
            submitted_by=user_key,
            created_date=timezone.now(),
            raw_data=result.get("raw_data", {}),
        )
        RIRSyncLog.objects.create(
            rir_config=network.rir_config,
            operation="delete",
            object_type="network",
            object_handle=network.handle,
            status="success",
            message=f"Delete request submitted, ticket {ticket.ticket_number}",
        )
        return Response(
            RIRTicketSerializer(ticket, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


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
