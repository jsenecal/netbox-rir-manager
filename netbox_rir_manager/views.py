import ipaddress

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport, ObjectAction
from netbox.views import generic

from netbox_rir_manager.backends.arin import ARINBackend
from netbox_rir_manager.choices import normalize_ticket_status
from netbox_rir_manager.filtersets import (
    RIRConfigFilterSet,
    RIRContactFilterSet,
    RIRCustomerFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSiteAddressFilterSet,
    RIRSyncLogFilterSet,
    RIRTicketFilterSet,
    RIRUserKeyFilterSet,
)
from netbox_rir_manager.forms import (
    RIRConfigBulkEditForm,
    RIRConfigFilterForm,
    RIRConfigForm,
    RIRConfigImportForm,
    RIRContactFilterForm,
    RIRContactForm,
    RIRCustomerFilterForm,
    RIRNetworkFilterForm,
    RIRNetworkForm,
    RIRNetworkReallocateForm,
    RIRNetworkReassignForm,
    RIROrganizationFilterForm,
    RIROrganizationForm,
    RIRSiteAddressForm,
    RIRTicketFilterForm,
    RIRUserKeyFilterForm,
    RIRUserKeyForm,
)
from netbox_rir_manager.models import (
    RIRConfig,
    RIRContact,
    RIRCustomer,
    RIRNetwork,
    RIROrganization,
    RIRSiteAddress,
    RIRSyncLog,
    RIRTicket,
    RIRUserKey,
)
from netbox_rir_manager.tables import (
    RIRConfigTable,
    RIRContactTable,
    RIRCustomerTable,
    RIRNetworkTable,
    RIROrganizationTable,
    RIRSiteAddressTable,
    RIRSyncLogTable,
    RIRTicketTable,
    RIRUserKeyTable,
)


# --- RIRConfig Views ---
class BulkSync(ObjectAction):
    name = "bulk_sync"
    label = "Sync Selected"
    multi = True
    permissions_required = {"change"}
    template_name = "netbox_rir_manager/buttons/bulk_sync.html"


class RIRConfigListView(generic.ObjectListView):
    queryset = RIRConfig.objects.all()
    table = RIRConfigTable
    filterset = RIRConfigFilterSet
    filterset_form = RIRConfigFilterForm
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkSync, BulkDelete)


class RIRConfigView(generic.ObjectView):
    queryset = RIRConfig.objects.all()


class RIRConfigEditView(generic.ObjectEditView):
    queryset = RIRConfig.objects.all()
    form = RIRConfigForm


class RIRConfigDeleteView(generic.ObjectDeleteView):
    queryset = RIRConfig.objects.all()


class RIRConfigBulkImportView(generic.BulkImportView):
    queryset = RIRConfig.objects.all()
    model_form = RIRConfigImportForm


class RIRConfigBulkEditView(generic.BulkEditView):
    queryset = RIRConfig.objects.all()
    filterset = RIRConfigFilterSet
    table = RIRConfigTable
    form = RIRConfigBulkEditForm


class RIRConfigBulkDeleteView(generic.BulkDeleteView):
    queryset = RIRConfig.objects.all()
    filterset = RIRConfigFilterSet
    table = RIRConfigTable


class RIRConfigBulkSyncView(LoginRequiredMixin, View):
    """Trigger sync jobs for multiple RIR configs at once."""

    def post(self, request):
        from netbox_rir_manager.jobs import SyncRIRConfigJob

        pk_list = [int(pk) for pk in request.POST.getlist("pk")]

        if "_confirm" in request.POST:
            configs = RIRConfig.objects.filter(pk__in=pk_list)
            synced = []
            skipped = []
            for config in configs:
                user_key = RIRUserKey.objects.filter(user=request.user, rir_config=config).first()
                if not user_key:
                    skipped.append(config.name)
                    continue
                SyncRIRConfigJob.enqueue(instance=config, user=request.user, user_id=request.user.pk)
                synced.append(config.name)

            if synced:
                messages.success(request, f"Sync jobs queued for: {', '.join(synced)}")
            if skipped:
                messages.warning(request, f"Skipped (no API key): {', '.join(skipped)}")

            return redirect(reverse("plugins:netbox_rir_manager:rirconfig_list"))

        configs = RIRConfig.objects.filter(pk__in=pk_list)
        table = RIRConfigTable(configs, orderable=False)
        if not table.rows:
            messages.warning(request, "No configs were selected.")
            return redirect(reverse("plugins:netbox_rir_manager:rirconfig_list"))

        return render(request, "netbox_rir_manager/rirconfig_bulk_sync.html", {
            "table": table,
            "pk_list": pk_list,
            "return_url": reverse("plugins:netbox_rir_manager:rirconfig_list"),
        })


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


# --- RIRCustomer Views ---
class RIRCustomerListView(generic.ObjectListView):
    queryset = RIRCustomer.objects.all()
    table = RIRCustomerTable
    filterset = RIRCustomerFilterSet
    filterset_form = RIRCustomerFilterForm


class RIRCustomerView(generic.ObjectView):
    queryset = RIRCustomer.objects.all()


class RIRCustomerDeleteView(generic.ObjectDeleteView):
    queryset = RIRCustomer.objects.all()


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


# --- RIRSiteAddress Views ---
class RIRSiteAddressListView(generic.ObjectListView):
    queryset = RIRSiteAddress.objects.all()
    table = RIRSiteAddressTable
    filterset = RIRSiteAddressFilterSet


class RIRSiteAddressView(generic.ObjectView):
    queryset = RIRSiteAddress.objects.all()


class RIRSiteAddressEditView(generic.ObjectEditView):
    queryset = RIRSiteAddress.objects.all()
    form = RIRSiteAddressForm


class RIRSiteAddressDeleteView(generic.ObjectDeleteView):
    queryset = RIRSiteAddress.objects.all()


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

            RIRCustomer.objects.create(
                rir_config=network.rir_config,
                handle=customer_result["handle"],
                customer_name=customer_data["customer_name"],
                street_address=customer_data.get("street_address", ""),
                city=customer_data.get("city", ""),
                state_province=customer_data.get("state_province", ""),
                postal_code=customer_data.get("postal_code", ""),
                country=customer_data.get("country", ""),
                network=network,
                raw_data=customer_result,
                created_date=timezone.now(),
            )

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
    """Remove a reassigned/reallocated network from ARIN (with confirmation page)."""

    def get(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        return render(
            request,
            "netbox_rir_manager/rirnetwork_confirm_remove.html",
            {"object": network},
        )

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
    """Delete a network at ARIN (creates a ticket, with confirmation page)."""

    def get(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        return render(
            request,
            "netbox_rir_manager/rirnetwork_confirm_delete_arin.html",
            {"object": network},
        )

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


# --- Aggregate Sync View (from Aggregate detail page) ---
class AggregateSyncView(LoginRequiredMixin, View):
    """Sync a single aggregate from ARIN."""

    def post(self, request, pk):
        from ipam.models import Aggregate

        aggregate = get_object_or_404(Aggregate, pk=pk)

        # Find the RIR config for this aggregate's RIR
        rir_config = RIRConfig.objects.filter(rir=aggregate.rir, is_active=True).first()
        if not rir_config:
            messages.error(request, "No active RIR config found for this aggregate's RIR.")
            return redirect(aggregate.get_absolute_url())

        # Get user's API key
        user_key = RIRUserKey.objects.filter(user=request.user, rir_config=rir_config).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(aggregate.get_absolute_url())

        backend = ARINBackend.from_rir_config(rir_config, api_key=user_key.api_key)

        # Sync this specific aggregate
        network = aggregate.prefix
        start_address = str(network.network)
        end_address = str(network.broadcast)

        net_data = backend.find_net(start_address, end_address)
        if net_data is None:
            messages.warning(request, "No matching network found at ARIN for this aggregate.")
            RIRSyncLog.objects.create(
                rir_config=rir_config,
                operation="sync",
                object_type="network",
                object_handle=str(aggregate.prefix),
                status="skipped",
                message=f"No ARIN network found for {aggregate.prefix}",
            )
            return redirect(aggregate.get_absolute_url())

        net, created = RIRNetwork.sync_from_arin(
            net_data, rir_config, aggregate=aggregate, user_key=user_key,
        )

        RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="network",
            object_handle=net_data["handle"],
            status="success",
            message=f"{'Created' if created else 'Updated'} network {net_data['handle']}",
        )

        action = "Created" if created else "Updated"
        messages.success(request, f"{action} RIR network {net.handle} from ARIN.")
        return redirect(aggregate.get_absolute_url())


# --- Prefix Sync View (from Prefix detail page) ---
class PrefixSyncView(LoginRequiredMixin, View):
    """Sync a single prefix from ARIN using mostSpecificNet."""

    def post(self, request, pk):
        from ipam.models import Aggregate, Prefix

        prefix = get_object_or_404(Prefix, pk=pk)

        # Find parent aggregate to determine RIR config
        agg = Aggregate.objects.filter(
            prefix__net_contains_or_equals=prefix.prefix
        ).first()
        if not agg:
            messages.error(request, "No parent aggregate found for this prefix.")
            return redirect(prefix.get_absolute_url())

        rir_config = RIRConfig.objects.filter(rir=agg.rir, is_active=True).first()
        if not rir_config:
            messages.error(request, "No active RIR config found for this prefix's RIR.")
            return redirect(prefix.get_absolute_url())

        user_key = RIRUserKey.objects.filter(user=request.user, rir_config=rir_config).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(prefix.get_absolute_url())

        backend = ARINBackend.from_rir_config(rir_config, api_key=user_key.api_key)

        network = ipaddress.ip_network(str(prefix.prefix), strict=False)
        start_address = str(network.network_address)
        end_address = str(network.broadcast_address)

        net_data = backend.find_net(start_address, end_address)
        if net_data is None:
            messages.warning(request, "No matching network found at ARIN for this prefix.")
            RIRSyncLog.objects.create(
                rir_config=rir_config,
                operation="sync",
                object_type="network",
                object_handle=str(prefix.prefix),
                status="skipped",
                message=f"No ARIN network found for {prefix.prefix}",
            )
            return redirect(prefix.get_absolute_url())

        # Check if this is actually a child net (not the parent aggregate's net)
        parent_network = RIRNetwork.objects.filter(aggregate=agg).first()
        if parent_network and net_data["handle"] == parent_network.handle:
            messages.info(
                request,
                "No separate reassignment found at ARIN -- this prefix is covered by the parent allocation.",
            )
            return redirect(prefix.get_absolute_url())

        net, created = RIRNetwork.sync_from_arin(
            net_data, rir_config, prefix=prefix, user_key=user_key,
        )

        RIRSyncLog.objects.create(
            rir_config=rir_config,
            operation="sync",
            object_type="network",
            object_handle=net_data["handle"],
            status="success",
            message=f"{'Created' if created else 'Updated'} network {net_data['handle']} for prefix {prefix.prefix}",
        )

        action = "Created" if created else "Updated"
        messages.success(request, f"{action} RIR network {net.handle} from ARIN.")
        return redirect(prefix.get_absolute_url())


# --- Prefix Reassign View (from Prefix detail page) ---
class PrefixReassignView(LoginRequiredMixin, View):
    """Reassign a prefix at ARIN from the Prefix detail page."""

    def get(self, request, pk):
        from ipam.models import Aggregate, Prefix

        prefix = get_object_or_404(Prefix, pk=pk)

        # Find parent RIRNetwork
        agg = Aggregate.objects.filter(
            prefix__net_contains_or_equals=prefix.prefix
        ).first()
        parent_network = RIRNetwork.objects.filter(aggregate=agg).first() if agg else None

        # Pre-fill form
        network = ipaddress.ip_network(str(prefix.prefix), strict=False)
        initial = {
            "start_address": str(network.network_address),
            "end_address": str(network.broadcast_address),
        }

        # Pre-fill from tenant
        if prefix.tenant:
            initial["customer_name"] = prefix.tenant.name

            # Check if tenant has a linked RIROrganization
            rir_org = RIROrganization.objects.filter(tenant=prefix.tenant).first()
            if rir_org:
                initial["reassignment_type"] = "detailed"
                initial["org_handle"] = rir_org.handle

        # Pre-fill from site address
        site = getattr(prefix, "_site", None) or getattr(prefix, "site", None)
        if site is None:
            from dcim.models import Site

            scope = getattr(prefix, "scope", None)
            if isinstance(scope, Site):
                site = scope

        if site:
            try:
                site_address = site.rir_address
                initial["street_address"] = site_address.street_address
                initial["city"] = site_address.city
                initial["state_province"] = site_address.state_province
                initial["postal_code"] = site_address.postal_code
                initial["country"] = site_address.country
            except RIRSiteAddress.DoesNotExist:
                pass

        # Generate net_name from tenant + prefix
        if prefix.tenant:
            initial["net_name"] = f"{prefix.tenant.name}-{prefix.prefix}"

        form = RIRNetworkReassignForm(initial=initial)

        return render(
            request,
            "netbox_rir_manager/prefix_reassign.html",
            {
                "object": prefix,
                "form": form,
                "parent_network": parent_network,
            },
        )

    def post(self, request, pk):
        from ipam.models import Aggregate, Prefix

        prefix = get_object_or_404(Prefix, pk=pk)
        form = RIRNetworkReassignForm(request.POST)

        # Find parent RIRNetwork
        agg = Aggregate.objects.filter(
            prefix__net_contains_or_equals=prefix.prefix
        ).first()
        parent_network = RIRNetwork.objects.filter(aggregate=agg).first() if agg else None

        if not form.is_valid():
            return render(
                request,
                "netbox_rir_manager/prefix_reassign.html",
                {
                    "object": prefix,
                    "form": form,
                    "parent_network": parent_network,
                },
            )

        if not parent_network:
            messages.error(request, "No parent RIR network found for this prefix.")
            return redirect(prefix.get_absolute_url())

        user_key = RIRUserKey.objects.filter(
            user=request.user,
            rir_config=parent_network.rir_config,
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(prefix.get_absolute_url())

        # Enqueue as background job
        from netbox_rir_manager.jobs import ReassignJob

        ReassignJob.enqueue(
            instance=parent_network.rir_config,
            user=request.user,
            prefix_id=prefix.pk,
            user_key_id=user_key.pk,
        )

        messages.success(request, f"Reassignment job queued for prefix {prefix.prefix}.")
        return redirect(prefix.get_absolute_url())


# --- Site Address Resolve View ---
class SiteAddressResolveView(LoginRequiredMixin, View):
    """Resolve a Site's address via geocoding."""

    def post(self, request, pk):
        from dcim.models import Site

        from netbox_rir_manager.services.geocoding import resolve_site_address

        site = get_object_or_404(Site, pk=pk)

        # Delete existing address if any (force re-resolve)
        RIRSiteAddress.objects.filter(site=site).delete()

        address = resolve_site_address(site)
        if address:
            messages.success(
                request,
                f"Address resolved: {address.city}, {address.state_province}, {address.country}",
            )
        else:
            messages.warning(request, "Could not resolve address for this site. Add coordinates or a physical address.")

        return redirect(site.get_absolute_url())
