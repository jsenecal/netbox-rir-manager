from netbox.views import generic

from netbox_rir_manager.filtersets import (
    RIRAccountFilterSet,
    RIRContactFilterSet,
    RIRNetworkFilterSet,
    RIROrganizationFilterSet,
    RIRSyncLogFilterSet,
)
from netbox_rir_manager.forms import (
    RIRAccountFilterForm,
    RIRAccountForm,
    RIRContactFilterForm,
    RIRContactForm,
    RIRNetworkFilterForm,
    RIRNetworkForm,
    RIROrganizationFilterForm,
    RIROrganizationForm,
)
from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog
from netbox_rir_manager.tables import (
    RIRAccountTable,
    RIRContactTable,
    RIRNetworkTable,
    RIROrganizationTable,
    RIRSyncLogTable,
)


# --- RIRAccount Views ---
class RIRAccountListView(generic.ObjectListView):
    queryset = RIRAccount.objects.all()
    table = RIRAccountTable
    filterset = RIRAccountFilterSet
    filterset_form = RIRAccountFilterForm


class RIRAccountView(generic.ObjectView):
    queryset = RIRAccount.objects.all()


class RIRAccountEditView(generic.ObjectEditView):
    queryset = RIRAccount.objects.all()
    form = RIRAccountForm


class RIRAccountDeleteView(generic.ObjectDeleteView):
    queryset = RIRAccount.objects.all()


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
