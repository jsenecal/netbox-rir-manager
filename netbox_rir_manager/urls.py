from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_rir_manager import views
from netbox_rir_manager.models import (
    RIRConfig,
    RIRContact,
    RIRNetwork,
    RIROrganization,
    RIRSyncLog,
    RIRTicket,
    RIRUserKey,
)

urlpatterns = [
    # RIRConfig
    path("configs/", views.RIRConfigListView.as_view(), name="rirconfig_list"),
    path("configs/add/", views.RIRConfigEditView.as_view(), name="rirconfig_add"),
    path("configs/<int:pk>/", views.RIRConfigView.as_view(), name="rirconfig"),
    path("configs/<int:pk>/edit/", views.RIRConfigEditView.as_view(), name="rirconfig_edit"),
    path("configs/<int:pk>/delete/", views.RIRConfigDeleteView.as_view(), name="rirconfig_delete"),
    path("configs/<int:pk>/sync/", views.RIRConfigSyncView.as_view(), name="rirconfig_sync"),
    path(
        "configs/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirconfig_changelog",
        kwargs={"model": RIRConfig},
    ),
    # RIROrganization
    path("organizations/", views.RIROrganizationListView.as_view(), name="rirorganization_list"),
    path("organizations/add/", views.RIROrganizationEditView.as_view(), name="rirorganization_add"),
    path("organizations/<int:pk>/", views.RIROrganizationView.as_view(), name="rirorganization"),
    path("organizations/<int:pk>/edit/", views.RIROrganizationEditView.as_view(), name="rirorganization_edit"),
    path("organizations/<int:pk>/delete/", views.RIROrganizationDeleteView.as_view(), name="rirorganization_delete"),
    path(
        "organizations/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirorganization_changelog",
        kwargs={"model": RIROrganization},
    ),
    # RIRContact
    path("contacts/", views.RIRContactListView.as_view(), name="rircontact_list"),
    path("contacts/add/", views.RIRContactEditView.as_view(), name="rircontact_add"),
    path("contacts/<int:pk>/", views.RIRContactView.as_view(), name="rircontact"),
    path("contacts/<int:pk>/edit/", views.RIRContactEditView.as_view(), name="rircontact_edit"),
    path("contacts/<int:pk>/delete/", views.RIRContactDeleteView.as_view(), name="rircontact_delete"),
    path(
        "contacts/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rircontact_changelog",
        kwargs={"model": RIRContact},
    ),
    # RIRNetwork
    path("networks/", views.RIRNetworkListView.as_view(), name="rirnetwork_list"),
    path("networks/add/", views.RIRNetworkEditView.as_view(), name="rirnetwork_add"),
    path("networks/<int:pk>/", views.RIRNetworkView.as_view(), name="rirnetwork"),
    path("networks/<int:pk>/edit/", views.RIRNetworkEditView.as_view(), name="rirnetwork_edit"),
    path("networks/<int:pk>/delete/", views.RIRNetworkDeleteView.as_view(), name="rirnetwork_delete"),
    path(
        "networks/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirnetwork_changelog",
        kwargs={"model": RIRNetwork},
    ),
    # RIRNetwork actions
    path("networks/<int:pk>/reassign/", views.RIRNetworkReassignView.as_view(), name="rirnetwork_reassign"),
    path("networks/<int:pk>/reallocate/", views.RIRNetworkReallocateView.as_view(), name="rirnetwork_reallocate"),
    path("networks/<int:pk>/remove/", views.RIRNetworkRemoveView.as_view(), name="rirnetwork_remove"),
    path("networks/<int:pk>/delete-arin/", views.RIRNetworkDeleteARINView.as_view(), name="rirnetwork_delete_arin"),
    # RIRSyncLog
    path("sync-logs/", views.RIRSyncLogListView.as_view(), name="rirsynclog_list"),
    path("sync-logs/<int:pk>/", views.RIRSyncLogView.as_view(), name="rirsynclog"),
    path("sync-logs/<int:pk>/delete/", views.RIRSyncLogDeleteView.as_view(), name="rirsynclog_delete"),
    path(
        "sync-logs/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirsynclog_changelog",
        kwargs={"model": RIRSyncLog},
    ),
    # RIRTicket
    path("tickets/", views.RIRTicketListView.as_view(), name="rirticket_list"),
    path("tickets/<int:pk>/", views.RIRTicketView.as_view(), name="rirticket"),
    path("tickets/<int:pk>/delete/", views.RIRTicketDeleteView.as_view(), name="rirticket_delete"),
    path("tickets/<int:pk>/refresh/", views.RIRTicketRefreshView.as_view(), name="rirticket_refresh"),
    path(
        "tickets/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="rirticket_changelog",
        kwargs={"model": RIRTicket},
    ),
    # RIRUserKey
    path("user-keys/", views.RIRUserKeyListView.as_view(), name="riruserkey_list"),
    path("user-keys/add/", views.RIRUserKeyEditView.as_view(), name="riruserkey_add"),
    path("user-keys/<int:pk>/", views.RIRUserKeyView.as_view(), name="riruserkey"),
    path("user-keys/<int:pk>/edit/", views.RIRUserKeyEditView.as_view(), name="riruserkey_edit"),
    path("user-keys/<int:pk>/delete/", views.RIRUserKeyDeleteView.as_view(), name="riruserkey_delete"),
    path(
        "user-keys/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="riruserkey_changelog",
        kwargs={"model": RIRUserKey},
    ),
]
