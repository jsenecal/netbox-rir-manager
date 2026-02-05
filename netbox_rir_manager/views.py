from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from netbox.views import generic

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.choices import normalize_ticket_status
from netbox_rir_manager.filtersets import (
    RIRConfigFilterSet,
    RIRContactFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSyncLogFilterSet,
    RIRTicketFilterSet,
    RIRUserKeyFilterSet,
)
from netbox_rir_manager.forms import (
    RIRConfigFilterForm,
    RIRConfigForm,
    RIRContactFilterForm,
    RIRContactForm,
    RIRNetworkFilterForm,
    RIRNetworkForm,
    RIRNetworkReallocateForm,
    RIRNetworkReassignForm,
    RIROrganizationFilterForm,
    RIROrganizationForm,
    RIRTicketFilterForm,
    RIRUserKeyFilterForm,
    RIRUserKeyForm,
)
from netbox_rir_manager.models import (
    RIRConfig,
    RIRContact,
    RIRNetwork,
    RIROrganization,
    RIRSyncLog,
    RIRTicket,
    RIRUserKey,
)
from netbox_rir_manager.tables import (
    RIRConfigTable,
    RIRContactTable,
    RIRNetworkTable,
    RIROrganizationTable,
    RIRSyncLogTable,
    RIRTicketTable,
    RIRUserKeyTable,
)


# --- RIRConfig Views ---
class RIRConfigListView(generic.ObjectListView):
    queryset = RIRConfig.objects.all()
    table = RIRConfigTable
    filterset = RIRConfigFilterSet
    filterset_form = RIRConfigFilterForm


class RIRConfigView(generic.ObjectView):
    queryset = RIRConfig.objects.all()


class RIRConfigEditView(generic.ObjectEditView):
    queryset = RIRConfig.objects.all()
    form = RIRConfigForm


class RIRConfigDeleteView(generic.ObjectDeleteView):
    queryset = RIRConfig.objects.all()


# --- RIROrganization Views ---
class RIROrganizationListView(generic.ObjectListView):
    queryset = RIROrganization.objects.all()
    table = RIROrganizationTable
    filterset = RIROrganizationFilterSet
    filterset_form = RIROrganizationFilterForm


class RIROrganizationView(generic.ObjectView):
    queryset = RIROrganization.objects.all()


class RIROrganizationEditView(generic.ObjectEditView):
    queryset = RIROrganization.objects.all()
    form = RIROrganizationForm


class RIROrganizationDeleteView(generic.ObjectDeleteView):
    queryset = RIROrganization.objects.all()


# --- RIRContact Views ---
class RIRContactListView(generic.ObjectListView):
    queryset = RIRContact.objects.all()
    table = RIRContactTable
    filterset = RIRContactFilterSet
    filterset_form = RIRContactFilterForm


class RIRContactView(generic.ObjectView):
    queryset = RIRContact.objects.all()


class RIRContactEditView(generic.ObjectEditView):
    queryset = RIRContact.objects.all()
    form = RIRContactForm


class RIRContactDeleteView(generic.ObjectDeleteView):
    queryset = RIRContact.objects.all()


# --- RIRNetwork Views ---
class RIRNetworkListView(generic.ObjectListView):
    queryset = RIRNetwork.objects.all()
    table = RIRNetworkTable
    filterset = RIRNetworkFilterSet
    filterset_form = RIRNetworkFilterForm


class RIRNetworkView(generic.ObjectView):
    queryset = RIRNetwork.objects.all()


class RIRNetworkEditView(generic.ObjectEditView):
    queryset = RIRNetwork.objects.all()
    form = RIRNetworkForm


class RIRNetworkDeleteView(generic.ObjectDeleteView):
    queryset = RIRNetwork.objects.all()


# --- RIRSyncLog Views ---
class RIRSyncLogListView(generic.ObjectListView):
    queryset = RIRSyncLog.objects.all()
    table = RIRSyncLogTable
    filterset = RIRSyncLogFilterSet


class RIRSyncLogView(generic.ObjectView):
    queryset = RIRSyncLog.objects.all()


class RIRSyncLogDeleteView(generic.ObjectDeleteView):
    queryset = RIRSyncLog.objects.all()


# --- RIRUserKey Views ---
class RIRUserKeyListView(generic.ObjectListView):
    queryset = RIRUserKey.objects.all()
    table = RIRUserKeyTable
    filterset = RIRUserKeyFilterSet
    filterset_form = RIRUserKeyFilterForm


class RIRUserKeyView(generic.ObjectView):
    queryset = RIRUserKey.objects.all()


class RIRUserKeyEditView(generic.ObjectEditView):
    queryset = RIRUserKey.objects.all()
    form = RIRUserKeyForm


class RIRUserKeyDeleteView(generic.ObjectDeleteView):
    queryset = RIRUserKey.objects.all()


# --- RIRTicket Views ---
class RIRTicketListView(generic.ObjectListView):
    queryset = RIRTicket.objects.all()
    table = RIRTicketTable
    filterset = RIRTicketFilterSet
    filterset_form = RIRTicketFilterForm


class RIRTicketView(generic.ObjectView):
    queryset = RIRTicket.objects.all()


class RIRTicketDeleteView(generic.ObjectDeleteView):
    queryset = RIRTicket.objects.all()


# --- Sync Trigger View ---
class RIRConfigSyncView(LoginRequiredMixin, View):
    """Trigger a background sync job for an RIRConfig."""

    def post(self, request, pk):
        from netbox_rir_manager.jobs import SyncRIRConfigJob
        from netbox_rir_manager.models import RIRUserKey as RIRUserKeyModel

        rir_config = get_object_or_404(RIRConfig, pk=pk)

        if not RIRUserKeyModel.objects.filter(user=request.user, rir_config=rir_config).exists():
            messages.error(request, "You don't have an API key configured for this RIR config.")
            return redirect(rir_config.get_absolute_url())

        SyncRIRConfigJob.enqueue(
            instance=rir_config,
            user=request.user,
            user_id=request.user.pk,
        )
        messages.success(request, f"Sync job queued for {rir_config.name}.")
        return redirect(rir_config.get_absolute_url())


class RIRTicketRefreshView(LoginRequiredMixin, View):
    """Refresh ticket status from ARIN (placeholder)."""

    def post(self, request, pk):
        ticket = get_object_or_404(RIRTicket, pk=pk)
        messages.info(request, f"Ticket {ticket.ticket_number} status is: {ticket.get_status_display()}")
        return redirect(ticket.get_absolute_url())


class RIRNetworkReassignView(LoginRequiredMixin, View):
    """Reassign a subnet from this network."""

    def get(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReassignForm()
        return render(
            request,
            "netbox_rir_manager/rirnetwork_reassign.html",
            {
                "object": network,
                "form": form,
            },
        )

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReassignForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "netbox_rir_manager/rirnetwork_reassign.html",
                {
                    "object": network,
                    "form": form,
                },
            )

        user_key = RIRUserKey.objects.filter(
            user=request.user,
            rir_config=network.rir_config,
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)

        rtype = form.cleaned_data["reassignment_type"]
        if rtype == "simple":
            customer_data = {
                "customer_name": form.cleaned_data["customer_name"],
                "street_address": form.cleaned_data.get("street_address", ""),
                "city": form.cleaned_data["city"],
                "state_province": form.cleaned_data.get("state_province", ""),
                "postal_code": form.cleaned_data.get("postal_code", ""),
                "country": form.cleaned_data["country"],
            }
            customer_result = backend.create_customer(network.handle, customer_data)
            if customer_result is None:
                messages.error(request, "Failed to create customer at ARIN.")
                RIRSyncLog.objects.create(
                    rir_config=network.rir_config,
                    operation="create",
                    object_type="customer",
                    object_handle=network.handle,
                    status="error",
                    message="Failed to create customer",
                )
                return redirect(network.get_absolute_url())

        net_data = {
            "net_name": form.cleaned_data.get("net_name", ""),
            "start_address": str(form.cleaned_data["start_address"]),
            "end_address": str(form.cleaned_data["end_address"]),
        }
        if rtype == "simple":
            net_data["customer_handle"] = customer_result["handle"]
        else:
            net_data["org_handle"] = form.cleaned_data["org_handle"]

        result = backend.reassign_network(network.handle, net_data)
        if result is None:
            messages.error(request, "Reassignment failed at ARIN.")
            RIRSyncLog.objects.create(
                rir_config=network.rir_config,
                operation="reassign",
                object_type="network",
                object_handle=network.handle,
                status="error",
                message="Reassignment failed",
            )
            return redirect(network.get_absolute_url())

        ticket = RIRTicket.objects.create(
            rir_config=network.rir_config,
            ticket_number=result.get("ticket_number", ""),
            ticket_type=result.get("ticket_type", "IPV4_SIMPLE_REASSIGN"),
            status=normalize_ticket_status(result.get("ticket_status", "")),
            network=network,
            submitted_by=user_key,
            created_date=timezone.now(),
            raw_data=result.get("raw_data", {}),
        )
        RIRSyncLog.objects.create(
            rir_config=network.rir_config,
            operation="reassign",
            object_type="network",
            object_handle=network.handle,
            status="success",
            message=f"Reassignment submitted, ticket {ticket.ticket_number}",
        )
        messages.success(request, f"Reassignment submitted. Ticket: {ticket.ticket_number}")
        return redirect(ticket.get_absolute_url())


class RIRNetworkReallocateView(LoginRequiredMixin, View):
    """Reallocate a subnet from this network."""

    def get(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReallocateForm()
        return render(
            request,
            "netbox_rir_manager/rirnetwork_reallocate.html",
            {
                "object": network,
                "form": form,
            },
        )

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReallocateForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "netbox_rir_manager/rirnetwork_reallocate.html",
                {
                    "object": network,
                    "form": form,
                },
            )

        user_key = RIRUserKey.objects.filter(
            user=request.user,
            rir_config=network.rir_config,
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        net_data = {
            "org_handle": form.cleaned_data["org_handle"],
            "net_name": form.cleaned_data.get("net_name", ""),
            "start_address": str(form.cleaned_data["start_address"]),
            "end_address": str(form.cleaned_data["end_address"]),
        }
        result = backend.reallocate_network(network.handle, net_data)
        if result is None:
            messages.error(request, "Reallocation failed at ARIN.")
            RIRSyncLog.objects.create(
                rir_config=network.rir_config,
                operation="reallocate",
                object_type="network",
                object_handle=network.handle,
                status="error",
                message="Reallocation failed",
            )
            return redirect(network.get_absolute_url())

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
        messages.success(request, f"Reallocation submitted. Ticket: {ticket.ticket_number}")
        return redirect(ticket.get_absolute_url())


class RIRNetworkRemoveView(LoginRequiredMixin, View):
    """Remove a reassigned/reallocated network from ARIN."""

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        user_key = RIRUserKey.objects.filter(
            user=request.user,
            rir_config=network.rir_config,
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

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
            messages.success(request, f"Network {network.handle} removed from ARIN.")
        else:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config,
                operation="remove",
                object_type="network",
                object_handle=network.handle,
                status="error",
                message="Failed to remove network from ARIN",
            )
            messages.error(request, "Failed to remove network from ARIN.")
        return redirect(network.get_absolute_url())


class RIRNetworkDeleteARINView(LoginRequiredMixin, View):
    """Delete a network at ARIN (creates a ticket)."""

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        user_key = RIRUserKey.objects.filter(
            user=request.user,
            rir_config=network.rir_config,
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

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
            messages.error(request, "Failed to delete network at ARIN.")
            return redirect(network.get_absolute_url())

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
        messages.success(request, f"Delete request submitted. Ticket: {ticket.ticket_number}")
        return redirect(ticket.get_absolute_url())
