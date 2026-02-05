from django.urls import path
from netbox.views.generic import ObjectChangeLogView

from netbox_rir_manager import views
from netbox_rir_manager.models import RIRConfig, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog

urlpatterns = [
    # RIRConfig
    path("configs/", views.RIRConfigListView.as_view(), name="rirconfig_list"),
    path("configs/add/", views.RIRConfigEditView.as_view(), name="rirconfig_add"),
    path("configs/<int:pk>/", views.RIRConfigView.as_view(), name="rirconfig"),
    path("configs/<int:pk>/edit/", views.RIRConfigEditView.as_view(), name="rirconfig_edit"),
    path("configs/<int:pk>/delete/", views.RIRConfigDeleteView.as_view(), name="rirconfig_delete"),
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
]
