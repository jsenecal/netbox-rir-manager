from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestRIRConfigViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirconfig_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_config):
        url = reverse("plugins:netbox_rir_manager:rirconfig", args=[rir_config.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_add_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirconfig_add")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_edit_view(self, admin_client, rir_config):
        url = reverse("plugins:netbox_rir_manager:rirconfig_edit", args=[rir_config.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_config):
        url = reverse("plugins:netbox_rir_manager:rirconfig_delete", args=[rir_config.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_changelog_view(self, admin_client, rir_config):
        url = reverse("plugins:netbox_rir_manager:rirconfig_changelog", args=[rir_config.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_list_view_with_data(self, admin_client, rir_config):
        url = reverse("plugins:netbox_rir_manager:rirconfig_list")
        response = admin_client.get(url)
        assert response.status_code == 200
        assert rir_config.name.encode() in response.content


@pytest.mark.django_db
class TestRIROrganizationViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirorganization_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_organization):
        url = reverse("plugins:netbox_rir_manager:rirorganization", args=[rir_organization.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_edit_view(self, admin_client, rir_organization):
        url = reverse("plugins:netbox_rir_manager:rirorganization_edit", args=[rir_organization.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_organization):
        url = reverse("plugins:netbox_rir_manager:rirorganization_delete", args=[rir_organization.pk])
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRContactViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rircontact_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_contact):
        url = reverse("plugins:netbox_rir_manager:rircontact", args=[rir_contact.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_edit_view(self, admin_client, rir_contact):
        url = reverse("plugins:netbox_rir_manager:rircontact_edit", args=[rir_contact.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_contact):
        url = reverse("plugins:netbox_rir_manager:rircontact_delete", args=[rir_contact.pk])
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRNetworkViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirnetwork_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_network):
        url = reverse("plugins:netbox_rir_manager:rirnetwork", args=[rir_network.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_edit_view(self, admin_client, rir_network):
        url = reverse("plugins:netbox_rir_manager:rirnetwork_edit", args=[rir_network.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_network):
        url = reverse("plugins:netbox_rir_manager:rirnetwork_delete", args=[rir_network.pk])
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRSyncLogViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirsynclog_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="TEST", status="success"
        )
        url = reverse("plugins:netbox_rir_manager:rirsynclog", args=[log.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="TEST", status="success"
        )
        url = reverse("plugins:netbox_rir_manager:rirsynclog_delete", args=[log.pk])
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRUserKeyViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:riruserkey_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_user_key):
        url = reverse("plugins:netbox_rir_manager:riruserkey", args=[rir_user_key.pk])
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRIRTicketViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:rirticket_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_ticket):
        url = reverse("plugins:netbox_rir_manager:rirticket", args=[rir_ticket.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_ticket):
        url = reverse("plugins:netbox_rir_manager:rirticket_delete", args=[rir_ticket.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_list_view_with_data(self, admin_client, rir_ticket):
        url = reverse("plugins:netbox_rir_manager:rirticket_list")
        response = admin_client.get(url)
        assert response.status_code == 200
        assert rir_ticket.ticket_number.encode() in response.content


@pytest.mark.django_db
class TestRIRConfigSyncView:
    def test_sync_without_key_shows_error(self, admin_client, rir_config):
        url = reverse("plugins:netbox_rir_manager:rirconfig_sync", args=[rir_config.pk])
        response = admin_client.post(url)
        assert response.status_code == 302  # redirect back

    def test_sync_requires_post(self, admin_client, rir_config):
        url = reverse("plugins:netbox_rir_manager:rirconfig_sync", args=[rir_config.pk])
        response = admin_client.get(url)
        assert response.status_code == 405  # Method Not Allowed


@pytest.mark.django_db
class TestUnauthenticatedAccess:
    def test_list_view_requires_login(self):
        from django.test import Client

        client = Client()
        url = reverse("plugins:netbox_rir_manager:rirconfig_list")
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
class TestRIRNetworkActionViews:
    def test_reassign_get(self, admin_client, rir_network):
        url = reverse("plugins:netbox_rir_manager:rirnetwork_reassign", args=[rir_network.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_reallocate_get(self, admin_client, rir_network):
        url = reverse("plugins:netbox_rir_manager:rirnetwork_reallocate", args=[rir_network.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reassign_simple_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.create_customer.return_value = {"handle": "C-TEST"}
        mock_backend.reassign_network.return_value = {
            "ticket_number": "TKT-REASSIGN-001",
            "ticket_type": "IPV4_SIMPLE_REASSIGN",
            "ticket_status": "PENDING_REVIEW",
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:rirnetwork_reassign", args=[rir_network.pk])
        response = admin_client.post(
            url,
            {
                "reassignment_type": "simple",
                "customer_name": "Test Customer",
                "city": "Testville",
                "country": "US",
                "start_address": "10.0.0.0",
                "end_address": "10.0.0.255",
            },
        )
        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.get(ticket_number="TKT-REASSIGN-001")
        assert response.status_code == 302
        assert response.url == ticket.get_absolute_url()
        assert ticket.ticket_type == "IPV4_SIMPLE_REASSIGN"

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reassign_no_api_key(self, mock_backend_cls, admin_client, rir_network):
        """Reassign without an API key should redirect with error."""
        url = reverse("plugins:netbox_rir_manager:rirnetwork_reassign", args=[rir_network.pk])
        response = admin_client.post(
            url,
            {
                "reassignment_type": "detailed",
                "org_handle": "TARGET-ORG",
                "start_address": "10.0.0.0",
                "end_address": "10.0.0.255",
            },
        )
        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_remove_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.remove_network.return_value = True
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:rirnetwork_remove", args=[rir_network.pk])
        response = admin_client.post(url)
        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()

        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.filter(object_handle=rir_network.handle, operation="remove", status="success").first()
        assert log is not None

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_remove_failure(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.remove_network.return_value = False
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:rirnetwork_remove", args=[rir_network.pk])
        response = admin_client.post(url)
        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()

        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.filter(object_handle=rir_network.handle, operation="remove", status="error").first()
        assert log is not None

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_delete_arin_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.delete_network.return_value = {
            "ticket_number": "TKT-DELETE-001",
            "ticket_type": "NET_DELETE_REQUEST",
            "ticket_status": "PENDING_REVIEW",
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:rirnetwork_delete_arin", args=[rir_network.pk])
        response = admin_client.post(url)

        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.get(ticket_number="TKT-DELETE-001")
        assert response.status_code == 302
        assert response.url == ticket.get_absolute_url()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_delete_arin_failure(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.delete_network.return_value = None
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:rirnetwork_delete_arin", args=[rir_network.pk])
        response = admin_client.post(url)
        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reallocate_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.reallocate_network.return_value = {
            "ticket_number": "TKT-REALLOC-001",
            "ticket_type": "IPV4_REALLOCATE",
            "ticket_status": "PENDING_REVIEW",
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:rirnetwork_reallocate", args=[rir_network.pk])
        response = admin_client.post(
            url,
            {
                "org_handle": "TARGET-ORG",
                "start_address": "10.0.0.0",
                "end_address": "10.0.0.255",
            },
        )

        from netbox_rir_manager.models import RIRTicket

        ticket = RIRTicket.objects.get(ticket_number="TKT-REALLOC-001")
        assert response.status_code == 302
        assert response.url == ticket.get_absolute_url()


@pytest.fixture
def legacy_setup(rir, rir_config, rir_user_key, admin_user):
    """A second config (sorted after the first) for another org, with a key for the same user."""
    from ipam.models import Aggregate

    from netbox_rir_manager.models import RIRConfig, RIRUserKey

    legacy = RIRConfig.objects.create(rir=rir, name="Z Legacy Config", org_handle="LEGACY-ARIN", is_active=True)
    RIRUserKey.objects.create(user=admin_user, rir_config=legacy, api_key="legacy-key")
    agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)
    return {"legacy": legacy, "agg": agg}


@pytest.mark.django_db
class TestAggregateSyncView:
    @patch("netbox_rir_manager.views.ARINBackend")
    def test_sync_attaches_net_to_config_whose_org_owns_it(self, mock_backend_cls, admin_client, legacy_setup):
        from netbox_rir_manager.models import RIRNetwork

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = {
            "handle": "NET-LEGACY-1",
            "org_handle": "LEGACY-ARIN",
            "parent_net_handle": "",
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:aggregate_sync", args=[legacy_setup["agg"].pk])
        response = admin_client.post(url)

        assert response.status_code == 302
        net = RIRNetwork.objects.get(handle="NET-LEGACY-1")
        assert net.rir_config == legacy_setup["legacy"]
        assert net.aggregate == legacy_setup["agg"]

    @pytest.mark.parametrize(
        "found",
        [
            pytest.param({"handle": "NET-THEIRS-1", "org_handle": "OTHER-ARIN", "parent_net_handle": ""}, id="foreign"),
            pytest.param(None, id="no-net-at-arin"),
        ],
    )
    @patch("netbox_rir_manager.views.ARINBackend")
    def test_sync_skips_aggregate_owned_by_no_config(self, mock_backend_cls, admin_client, legacy_setup, found):
        from netbox_rir_manager.models import RIRNetwork, RIRSyncLog

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = found
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins:netbox_rir_manager:aggregate_sync", args=[legacy_setup["agg"].pk])
        admin_client.post(url)

        assert not RIRNetwork.objects.exists()
        assert list(RIRSyncLog.objects.values_list("status", flat=True)) == ["skipped", "skipped"]

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_sync_without_key_does_not_query_arin(self, mock_backend_cls, admin_client, rir_config, rir):
        from ipam.models import Aggregate

        agg = Aggregate.objects.create(prefix="192.0.2.0/24", rir=rir)

        admin_client.post(reverse("plugins:netbox_rir_manager:aggregate_sync", args=[agg.pk]))

        mock_backend_cls.from_rir_config.assert_not_called()


@pytest.mark.django_db
class TestPrefixSyncView:
    @patch("netbox_rir_manager.views.ARINBackend")
    def test_sync_uses_config_that_owns_parent_aggregate(self, mock_backend_cls, admin_client, legacy_setup):
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        RIRNetwork.objects.create(
            rir_config=legacy_setup["legacy"], handle="NET-LEGACY-1", aggregate=legacy_setup["agg"]
        )
        pfx = Prefix.objects.create(prefix="192.0.2.0/28")

        mock_backend = MagicMock()
        mock_backend.find_net.return_value = {"handle": "NET-CUST-1", "customer_handle": "C1", "raw_data": {}}
        mock_backend_cls.from_rir_config.return_value = mock_backend

        admin_client.post(reverse("plugins:netbox_rir_manager:prefix_sync", args=[pfx.pk]))

        mock_backend_cls.from_rir_config.assert_called_once_with(legacy_setup["legacy"], api_key="legacy-key")
        net = RIRNetwork.objects.get(handle="NET-CUST-1")
        assert net.rir_config == legacy_setup["legacy"]
        assert net.prefix == pfx

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_sync_refuses_prefix_under_unlinked_aggregate(self, mock_backend_cls, admin_client, legacy_setup):
        from ipam.models import Prefix

        from netbox_rir_manager.models import RIRNetwork

        pfx = Prefix.objects.create(prefix="192.0.2.0/28")

        admin_client.post(reverse("plugins:netbox_rir_manager:prefix_sync", args=[pfx.pk]))

        mock_backend_cls.from_rir_config.assert_not_called()
        assert not RIRNetwork.objects.exists()
