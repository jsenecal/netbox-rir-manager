from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from netbox.views import generic

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
