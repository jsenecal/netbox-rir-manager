import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from netbox.object_actions import (
    AddObject,
    BulkDelete,
    BulkEdit,
    BulkExport,
    BulkImport,
    DeleteObject,
    ObjectAction,
)
from netbox.views import generic
from utilities.permissions import get_permission_for_model
from utilities.views import ObjectPermissionRequiredMixin

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
from netbox_rir_manager.forms import (
    RIRAddressFilterForm,
    RIRAddressForm,
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
    RIRTicketFilterForm,
    RIRUserKeyFilterForm,
    RIRUserKeyForm,
)
from netbox_rir_manager.ip_ranges import prefix_range
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
from netbox_rir_manager.net_names import build_net_name
from netbox_rir_manager.services.arin_results import ARINWriteError
from netbox_rir_manager.services.net_writes import (
    reallocation_request,
    submit_net_delete,
    submit_net_remove,
    submit_reallocation,
)
from netbox_rir_manager.services.reassignment import (
    prefix_site,
    reassignment_request,
    submit_reassignment,
)
from netbox_rir_manager.tables import (
    RIRAddressTable,
    RIRConfigTable,
    RIRContactTable,
    RIRCustomerTable,
    RIRNetworkTable,
    RIROrganizationTable,
    RIRSyncLogTable,
    RIRTicketTable,
    RIRUserKeyTable,
)


class RIRActionPermissionMixin(ObjectPermissionRequiredMixin):
    """Require the add permission on the queryset's model, as the matching REST API action does.

    The REST API runs custom actions as POST requests, so NetBox requires add_<model> on them and
    restricts the object to that permission's constraints. NetBox's mixin does the same here: it
    denies users without the permission and restricts self.queryset to the objects they may act on.
    """

    queryset = None

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "add")

    def require_permitted(self, obj, message):
        """Refuse when obj is outside the objects the user's permission lets them act on."""
        if not self.queryset.filter(pk=obj.pk).exists():
            raise PermissionDenied(message)


def restricted_or_404(model, request, pk, action="view"):
    """The NetBox object pk, if the user's action permission covers it."""
    return get_object_or_404(model.objects.restrict(request.user, action), pk=pk)


def arin_outcome_redirect(request, outcome, fallback_url):
    """Report a write ARIN accepted, then open its ticket, or fallback_url when there is none."""
    if not outcome.recorded:
        messages.warning(request, outcome.message)
    else:
        messages.success(request, outcome.message)
    return redirect(outcome.ticket.get_absolute_url() if outcome.ticket else fallback_url)


# --- RIRConfig Views ---
class BulkSync(ObjectAction):
    name = "bulk_sync"
    label = "Sync Selected"
    multi = True
    permissions_required = {"add"}
    template_name = "netbox_rir_manager/buttons/bulk_sync.html"


class RIRConfigListView(generic.ObjectListView):
    queryset = RIRConfig.objects.all()
    table = RIRConfigTable
    filterset = RIRConfigFilterSet
    filterset_form = RIRConfigFilterForm
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkSync, BulkDelete)


class RIRConfigView(generic.ObjectView):
    queryset = RIRConfig.objects.all()

    def get_extra_context(self, request, instance):
        return {"can_sync": request.user.has_perm("netbox_rir_manager.add_rirconfig", instance)}


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


class RIRConfigBulkSyncView(RIRActionPermissionMixin, View):
    """Trigger sync jobs for multiple RIR configs at once.

    Only the selected configs the user's add_rirconfig permission covers are synced.
    """

    queryset = RIRConfig.objects.all()

    def post(self, request):
        from netbox_rir_manager.jobs import SyncRIRConfigJob

        pk_list = [int(pk) for pk in request.POST.getlist("pk")]

        if "_confirm" in request.POST:
            configs = self.queryset.filter(pk__in=pk_list)
            synced = []
            skipped = []
            for config in configs:
                user_key = config.resolve_key(request.user)
                if not user_key:
                    skipped.append(config.name)
                    continue
                SyncRIRConfigJob.enqueue(instance=config, user=request.user)
                synced.append(config.name)

            if synced:
                messages.success(request, f"Sync jobs queued for: {', '.join(synced)}")
            if skipped:
                messages.warning(request, f"Skipped (no API key): {', '.join(skipped)}")

            return redirect(reverse("plugins:netbox_rir_manager:rirconfig_list"))

        configs = self.queryset.filter(pk__in=pk_list)
        table = RIRConfigTable(configs, orderable=False)
        if not table.rows:
            messages.warning(request, "No configs were selected.")
            return redirect(reverse("plugins:netbox_rir_manager:rirconfig_list"))

        return render(
            request,
            "netbox_rir_manager/rirconfig_bulk_sync.html",
            {
                "table": table,
                "pk_list": pk_list,
                "return_url": reverse("plugins:netbox_rir_manager:rirconfig_list"),
            },
        )


# --- RIROrganization Views ---
class RIROrganizationListView(generic.ObjectListView):
    queryset = RIROrganization.objects.select_related("address").all()
    table = RIROrganizationTable
    filterset = RIROrganizationFilterSet
    filterset_form = RIROrganizationFilterForm


class RIROrganizationView(generic.ObjectView):
    queryset = RIROrganization.objects.select_related("address").all()


class RIROrganizationEditView(generic.ObjectEditView):
    queryset = RIROrganization.objects.all()
    form = RIROrganizationForm


class RIROrganizationDeleteView(generic.ObjectDeleteView):
    queryset = RIROrganization.objects.all()


# --- RIRContact Views ---
class RIRContactListView(generic.ObjectListView):
    queryset = RIRContact.objects.select_related("address").all()
    table = RIRContactTable
    filterset = RIRContactFilterSet
    filterset_form = RIRContactFilterForm


class RIRContactView(generic.ObjectView):
    queryset = RIRContact.objects.select_related("address").all()


class RIRContactEditView(generic.ObjectEditView):
    queryset = RIRContact.objects.all()
    form = RIRContactForm


class RIRContactDeleteView(generic.ObjectDeleteView):
    queryset = RIRContact.objects.all()


# --- RIRCustomer Views ---
class RIRCustomerListView(generic.ObjectListView):
    queryset = RIRCustomer.objects.select_related("address").all()
    table = RIRCustomerTable
    filterset = RIRCustomerFilterSet
    filterset_form = RIRCustomerFilterForm
    actions = (BulkExport, BulkDelete)


class RIRCustomerView(generic.ObjectView):
    queryset = RIRCustomer.objects.select_related("address").all()
    actions = (DeleteObject,)


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

    def get_extra_context(self, request, instance):
        return {"can_act_at_arin": request.user.has_perm("netbox_rir_manager.add_rirnetwork", instance)}


class RIRNetworkEditView(generic.ObjectEditView):
    queryset = RIRNetwork.objects.all()
    form = RIRNetworkForm


class RIRNetworkDeleteView(generic.ObjectDeleteView):
    queryset = RIRNetwork.objects.all()


# --- RIRAddress Views ---
class RIRAddressListView(generic.ObjectListView):
    queryset = RIRAddress.objects.all()
    table = RIRAddressTable
    filterset = RIRAddressFilterSet
    filterset_form = RIRAddressFilterForm


class RIRAddressView(generic.ObjectView):
    queryset = RIRAddress.objects.all()


class RIRAddressEditView(generic.ObjectEditView):
    queryset = RIRAddress.objects.all()
    form = RIRAddressForm


class RIRAddressDeleteView(generic.ObjectDeleteView):
    queryset = RIRAddress.objects.all()


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

    def get_extra_context(self, request, instance):
        return {"can_refresh": request.user.has_perm("netbox_rir_manager.add_rirticket", instance)}


class RIRTicketDeleteView(generic.ObjectDeleteView):
    queryset = RIRTicket.objects.all()


# --- Sync Trigger View ---
class RIRConfigSyncView(RIRActionPermissionMixin, View):
    """Trigger a background sync job for an RIRConfig."""

    queryset = RIRConfig.objects.all()

    def post(self, request, pk):
        from netbox_rir_manager.jobs import SyncRIRConfigJob

        rir_config = get_object_or_404(self.queryset, pk=pk)

        if not rir_config.resolve_key(request.user):
            messages.error(request, NO_API_KEY_MESSAGE)
            return redirect(rir_config.get_absolute_url())

        SyncRIRConfigJob.enqueue(instance=rir_config, user=request.user)
        messages.success(request, f"Sync job queued for {rir_config.name}.")
        return_url = request.GET.get("return_url") or request.POST.get("return_url")
        return redirect(return_url or rir_config.get_absolute_url())


class RIRTicketRefreshView(RIRActionPermissionMixin, View):
    """Refresh ticket status from ARIN (placeholder)."""

    queryset = RIRTicket.objects.all()

    def post(self, request, pk):
        ticket = get_object_or_404(self.queryset, pk=pk)
        messages.info(request, f"Ticket {ticket.ticket_number} status is: {ticket.get_status_display()}")
        return redirect(ticket.get_absolute_url())


class RIRNetworkReassignView(RIRActionPermissionMixin, View):
    """Reassign a subnet from this network."""

    queryset = RIRNetwork.objects.all()

    def get(self, request, pk):
        network = get_object_or_404(self.queryset, pk=pk)
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
        network = get_object_or_404(self.queryset, pk=pk)
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

        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            messages.error(request, NO_API_KEY_MESSAGE)
            return redirect(network.get_absolute_url())

        backend = ARINBackend.for_user_key(user_key)
        net, customer, org_handle = reassignment_request(form.cleaned_data)
        try:
            outcome = submit_reassignment(backend, network, user_key, net, customer=customer, org_handle=org_handle)
        except ARINWriteError as exc:
            messages.error(request, str(exc))
            return redirect(network.get_absolute_url())

        return arin_outcome_redirect(request, outcome, network.get_absolute_url())


class RIRNetworkReallocateView(RIRActionPermissionMixin, View):
    """Reallocate a subnet from this network."""

    queryset = RIRNetwork.objects.all()

    def get(self, request, pk):
        network = get_object_or_404(self.queryset, pk=pk)
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
        network = get_object_or_404(self.queryset, pk=pk)
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

        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            messages.error(request, NO_API_KEY_MESSAGE)
            return redirect(network.get_absolute_url())

        backend = ARINBackend.for_user_key(user_key)
        net = reallocation_request(form.cleaned_data)
        try:
            outcome = submit_reallocation(backend, network, user_key, net)
        except ARINWriteError as exc:
            messages.error(request, str(exc))
            return redirect(network.get_absolute_url())
        return arin_outcome_redirect(request, outcome, network.get_absolute_url())


class RIRNetworkRemoveView(RIRActionPermissionMixin, View):
    """Remove a reassigned/reallocated network from ARIN (with confirmation page)."""

    queryset = RIRNetwork.objects.all()

    def get(self, request, pk):
        network = get_object_or_404(self.queryset, pk=pk)
        return render(
            request,
            "netbox_rir_manager/rirnetwork_confirm_remove.html",
            {"object": network},
        )

    def post(self, request, pk):
        network = get_object_or_404(self.queryset, pk=pk)
        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            messages.error(request, NO_API_KEY_MESSAGE)
            return redirect(network.get_absolute_url())

        backend = ARINBackend.for_user_key(user_key)
        try:
            submit_net_remove(backend, network)
        except ARINWriteError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Network {network.handle} removed from ARIN.")
        return redirect(network.get_absolute_url())


class RIRNetworkDeleteARINView(RIRActionPermissionMixin, View):
    """Delete a network at ARIN, with a confirmation page."""

    queryset = RIRNetwork.objects.all()

    def get(self, request, pk):
        network = get_object_or_404(self.queryset, pk=pk)
        return render(
            request,
            "netbox_rir_manager/rirnetwork_confirm_delete_arin.html",
            {"object": network},
        )

    def post(self, request, pk):
        network = get_object_or_404(self.queryset, pk=pk)
        user_key = network.rir_config.resolve_key(request.user)
        if not user_key:
            messages.error(request, NO_API_KEY_MESSAGE)
            return redirect(network.get_absolute_url())

        backend = ARINBackend.for_user_key(user_key)
        try:
            outcome = submit_net_delete(backend, network, user_key)
        except ARINWriteError as exc:
            messages.error(request, str(exc))
            return redirect(network.get_absolute_url())
        return arin_outcome_redirect(request, outcome, network.get_absolute_url())


# --- Aggregate Sync View (from Aggregate detail page) ---
class AggregateSyncView(RIRActionPermissionMixin, View):
    """Sync a single aggregate from ARIN.

    Syncing is what a config's Sync does for each of its aggregates, so this needs add_rirconfig,
    and only configs that permission covers are tried.
    """

    queryset = RIRConfig.objects.all()

    def post(self, request, pk):
        from ipam.models import Aggregate

        from netbox_rir_manager.jobs import sync_aggregate

        aggregate = restricted_or_404(Aggregate, request, pk)

        # Several active configs (one per org) can share an RIR; the aggregate belongs to
        # whichever one's org it is registered to, so try each config the user holds a key for.
        active = RIRConfig.objects.filter(rir=aggregate.rir, is_active=True)
        configs = self.queryset.filter(pk__in=active)
        if active.exists() and not configs.exists():
            raise PermissionDenied("You may not sync any active RIR config for this aggregate's RIR.")
        user_keys = [key for key in (config.resolve_key(request.user) for config in configs) if key]
        if not user_keys:
            messages.error(request, "No API key configured for an active RIR config on this aggregate's RIR.")
            return redirect(aggregate.get_absolute_url())

        for user_key in user_keys:
            rir_config = user_key.rir_config
            backend = ARINBackend.for_user_key(user_key)
            sync_log, net = sync_aggregate(backend, rir_config, aggregate, user_key=user_key)
            if net:
                messages.success(request, f"{sync_log.message} from ARIN.")
                return redirect(aggregate.get_absolute_url())

        messages.warning(request, "No network registered to your RIR configs' orgs covers this aggregate at ARIN.")
        return redirect(aggregate.get_absolute_url())


# --- Prefix Sync View (from Prefix detail page) ---
class PrefixSyncView(RIRActionPermissionMixin, View):
    """Sync a single prefix from ARIN using mostSpecificNet.

    Needs add_rirconfig on the config that owns the parent network, as for the aggregate Sync.
    """

    queryset = RIRConfig.objects.all()

    def post(self, request, pk):
        from ipam.models import Prefix

        prefix = restricted_or_404(Prefix, request, pk)

        # The prefix belongs to whichever config's org holds the net anchoring its aggregate.
        parent_network, agg = RIRNetwork.find_for_prefix(prefix)
        if not agg:
            messages.error(request, "No parent aggregate found for this prefix.")
            return redirect(prefix.get_absolute_url())
        if not parent_network or not parent_network.rir_config.is_active:
            messages.error(
                request,
                f"Aggregate {agg.prefix} is not linked to an active RIR config. Sync the aggregate first.",
            )
            return redirect(prefix.get_absolute_url())

        rir_config = parent_network.rir_config
        self.require_permitted(rir_config, f"You may not sync RIR config {rir_config}.")

        user_key = rir_config.resolve_key(request.user)
        if not user_key:
            messages.error(request, NO_API_KEY_MESSAGE)
            return redirect(prefix.get_absolute_url())

        backend = ARINBackend.for_user_key(user_key)

        net_data = backend.find_net(*prefix_range(prefix.prefix))
        if net_data is None:
            messages.warning(request, "No matching network found at ARIN for this prefix.")
            RIRSyncLog.log_skipped(rir_config, "sync", str(prefix.prefix), f"No ARIN network found for {prefix.prefix}")
            return redirect(prefix.get_absolute_url())

        # Check if this is actually a child net (not the parent aggregate's net)
        if net_data["handle"] == parent_network.handle:
            messages.info(
                request,
                "No separate reassignment found at ARIN -- this prefix is covered by the parent allocation.",
            )
            return redirect(prefix.get_absolute_url())

        net, created = RIRNetwork.sync_from_arin(
            net_data,
            rir_config,
            prefix=prefix,
            user_key=user_key,
        )

        RIRSyncLog.log_synced(rir_config, "network", net_data["handle"], created, f" for prefix {prefix.prefix}")

        action = "Created" if created else "Updated"
        messages.success(request, f"{action} RIR network {net.handle} from ARIN.")
        return redirect(prefix.get_absolute_url())


# --- Prefix Reassign View (from Prefix detail page) ---
class PrefixReassignView(RIRActionPermissionMixin, View):
    """Reassign a prefix at ARIN from the Prefix detail page.

    This reassigns from the parent network, so it needs add_rirnetwork on that network, as the
    network's own Reassign does.
    """

    queryset = RIRNetwork.objects.all()

    def get_targets(self, request, pk):
        """The prefix and its parent network, refused when the user may not act on that network."""
        from ipam.models import Prefix

        prefix = restricted_or_404(Prefix, request, pk)
        parent_network, _agg = RIRNetwork.find_for_prefix(prefix)
        if parent_network:
            self.require_permitted(parent_network, f"You may not reassign from RIR network {parent_network.handle}.")
        return prefix, parent_network

    def get(self, request, pk):
        prefix, parent_network = self.get_targets(request, pk)

        # Pre-fill form
        start_address, end_address = prefix_range(prefix.prefix)
        initial = {"start_address": start_address, "end_address": end_address}

        # Pre-fill from tenant
        if prefix.tenant:
            initial["customer_name"] = prefix.tenant.name

            # Check if tenant has a linked RIROrganization
            rir_org = RIROrganization.objects.filter(tenant=prefix.tenant).first()
            if rir_org:
                initial["reassignment_type"] = "detailed"
                initial["org_handle"] = rir_org.handle

        # Pre-fill from site address
        site = prefix_site(prefix)
        if site:
            site_address = RIRAddress.get_for_site(site)
            if site_address:
                initial.update(site_address.address_fields())

        if prefix.tenant:
            initial["net_name"] = build_net_name(prefix.tenant.name, prefix.prefix)

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
        prefix, parent_network = self.get_targets(request, pk)
        form = RIRNetworkReassignForm(request.POST)

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

        user_key = parent_network.rir_config.resolve_key(request.user)
        if not user_key:
            messages.error(request, NO_API_KEY_MESSAGE)
            return redirect(prefix.get_absolute_url())

        backend = ARINBackend.for_user_key(user_key)
        net, customer, org_handle = reassignment_request(form.cleaned_data)
        try:
            outcome = submit_reassignment(
                backend,
                parent_network,
                user_key,
                net,
                customer=customer,
                org_handle=org_handle,
                tenant=prefix.tenant,
                prefix=prefix,
            )
        except ARINWriteError as exc:
            messages.error(request, str(exc))
            return redirect(prefix.get_absolute_url())

        return arin_outcome_redirect(request, outcome, prefix.get_absolute_url())


# --- Site Address Resolve Views ---
class SiteAddressResolveModalView(RIRActionPermissionMixin, View):
    """Return HTMX modal content with geocoding candidates for a Site.

    This is the form for SiteAddressSelectView, so it needs the same add_riraddress permission.
    """

    queryset = RIRAddress.objects.all()
    template_name = "netbox_rir_manager/htmx/site_address_resolve_modal.html"

    def get(self, request, pk):
        from dcim.models import Site

        from netbox_rir_manager.services.geocoding import resolve_site_address_candidates

        site = restricted_or_404(Site, request, pk)
        candidates = resolve_site_address_candidates(site)

        # Pre-fill search field based on which source produced results:
        # reverse geocode from coords -> show coords, forward geocode -> show address
        if site.latitude and site.longitude:
            search_query = f"{site.latitude}, {site.longitude}"
        elif site.physical_address:
            search_query = site.physical_address
        else:
            search_query = ""

        return render(
            request,
            self.template_name,
            {
                "site": site,
                "candidates": candidates,
                "search_query": search_query,
            },
        )

    def post(self, request, pk):
        from dcim.models import Site

        from netbox_rir_manager.services.geocoding import resolve_site_address_candidates

        site = restricted_or_404(Site, request, pk)
        query = request.POST.get("query", "").strip()
        candidates = resolve_site_address_candidates(site, query=query or None)

        return render(
            request,
            self.template_name,
            {
                "site": site,
                "candidates": candidates,
                "search_query": query,
            },
        )


class SiteAddressSelectView(RIRActionPermissionMixin, View):
    """Create an RIRAddress from a selected geocoding candidate.

    Needs add_riraddress, and the saved address must fall within that permission's constraints,
    as NetBox requires for an object created through its edit views.
    """

    queryset = RIRAddress.objects.all()

    def post(self, request, pk):
        from dcim.models import Site

        site = restricted_or_404(Site, request, pk)

        street_address = request.POST.get("street_address", "")
        city = request.POST.get("city", "")
        state_province = request.POST.get("state_province", "")
        postal_code = request.POST.get("postal_code", "")
        country = request.POST.get("country", "")
        raw_geocode_str = request.POST.get("raw_geocode", "{}")

        try:
            raw_geocode = json.loads(raw_geocode_str)
        except (json.JSONDecodeError, TypeError):
            raw_geocode = {}

        # A rejected address is rolled back with the delete that preceded it.
        with transaction.atomic():
            # Delete existing site-level address (not location-specific ones)
            RIRAddress.objects.filter(site=site, location__isnull=True).delete()

            # Use get_or_create on address fields to handle unique constraint
            address, created = RIRAddress.objects.get_or_create(
                street_address=street_address,
                city=city,
                state_province=state_province,
                postal_code=postal_code,
                country=country,
                defaults={
                    "raw_geocode": raw_geocode,
                    "auto_resolved": True,
                    "last_resolved": timezone.now(),
                },
            )

            # Assign site FK (whether newly created or existing)
            address.site = site
            address.auto_resolved = True
            address.last_resolved = timezone.now()
            if raw_geocode:
                address.raw_geocode = raw_geocode
            address.save()

            self.require_permitted(address, "The selected address is outside your RIR address permission.")

        return HttpResponse(status=204, headers={"HX-Redirect": site.get_absolute_url()})
