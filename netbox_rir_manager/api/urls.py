from netbox.api.routers import NetBoxRouter

from netbox_rir_manager.api import views

router = NetBoxRouter()
router.register("accounts", views.RIRAccountViewSet)
router.register("organizations", views.RIROrganizationViewSet)
router.register("contacts", views.RIRContactViewSet)
router.register("networks", views.RIRNetworkViewSet)
router.register("sync-logs", views.RIRSyncLogViewSet)

urlpatterns = router.urls
