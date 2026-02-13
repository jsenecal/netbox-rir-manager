from netbox.api.routers import NetBoxRouter

from netbox_rir_manager.api import views

router = NetBoxRouter()
router.register("configs", views.RIRConfigViewSet)
router.register("organizations", views.RIROrganizationViewSet)
router.register("contacts", views.RIRContactViewSet)
router.register("customers", views.RIRCustomerViewSet)
router.register("networks", views.RIRNetworkViewSet)
router.register("site-addresses", views.RIRSiteAddressViewSet)
router.register("sync-logs", views.RIRSyncLogViewSet)
router.register("tickets", views.RIRTicketViewSet)
router.register("user-keys", views.RIRUserKeyViewSet)

urlpatterns = router.urls
