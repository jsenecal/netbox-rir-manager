from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from tests.arin_payloads import (
    DETAILED,
    EXISTING_TICKET,
    REALLOCATION,
    WRITE_FAILURES,
    immediate_result,
    ticket_result,
)


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


def _action_url(action, network):
    return reverse(f"plugins:netbox_rir_manager:rirnetwork_{action}", args=[network.pk])


def _messages(response):
    from django.contrib.messages import get_messages

    return [(m.level_tag, str(m)) for m in get_messages(response.wsgi_request)]


@pytest.mark.django_db
class TestRIRNetworkActionViews:
    def test_reassign_get(self, admin_client, rir_network):
        response = admin_client.get(_action_url("reassign", rir_network))
        assert response.status_code == 200

    def test_reallocate_get(self, admin_client, rir_network):
        response = admin_client.get(_action_url("reallocate", rir_network))
        assert response.status_code == 200

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reassign_simple_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        backend = mock_backend_cls.from_rir_config.return_value
        backend.create_customer.return_value = {"handle": "C-TEST"}
        backend.reassign_network.return_value = ticket_result("TKT-REASSIGN-001", "IPV4_SIMPLE_REASSIGN")

        response = admin_client.post(
            _action_url("reassign", rir_network),
            {
                "reassignment_type": "simple",
                "customer_name": "Test Customer",
                "city": "Testville",
                "country": "US",
                "start_address": "10.0.0.0",
                "end_address": "10.0.0.255",
            },
        )

        ticket = RIRTicket.objects.get(ticket_number="TKT-REASSIGN-001")
        assert response.status_code == 302
        assert response.url == ticket.get_absolute_url()
        assert ticket.ticket_type == "IPV4_SIMPLE_REASSIGN"

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reassign_no_api_key(self, mock_backend_cls, admin_client, rir_network):
        """Reassign without an API key should redirect with error."""
        response = admin_client.post(_action_url("reassign", rir_network), DETAILED)
        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_remove_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRSyncLog

        mock_backend_cls.from_rir_config.return_value.remove_network.return_value = True

        response = admin_client.post(_action_url("remove", rir_network))

        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()
        assert _messages(response) == [("success", f"Network {rir_network.handle} removed from ARIN.")]
        log = RIRSyncLog.objects.get(operation="remove")
        assert (log.status, log.message) == ("success", f"Removed network {rir_network.handle} from ARIN")

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_delete_arin_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        backend = mock_backend_cls.from_rir_config.return_value
        backend.delete_network.return_value = ticket_result("TKT-DELETE-001", "NET_DELETE_REQUEST")

        response = admin_client.post(_action_url("delete_arin", rir_network))

        ticket = RIRTicket.objects.get(ticket_number="TKT-DELETE-001")
        assert response.status_code == 302
        assert response.url == ticket.get_absolute_url()
        backend.delete_network.assert_called_once_with(rir_network.handle)

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reallocate_success(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        backend = mock_backend_cls.from_rir_config.return_value
        backend.reallocate_network.return_value = ticket_result("TKT-REALLOC-001", "IPV4_REALLOCATE")

        response = admin_client.post(_action_url("reallocate", rir_network), REALLOCATION)

        ticket = RIRTicket.objects.get(ticket_number="TKT-REALLOC-001")
        assert response.status_code == 302
        assert response.url == ticket.get_absolute_url()
        assert backend.reallocate_network.call_args[0] == (
            rir_network.handle,
            {"org_handle": "TARGET-ORG", "net_name": "", "start_address": "192.0.2.0", "end_address": "192.0.2.15"},
        )

    @pytest.mark.parametrize(
        "failure, action",
        [("reassign", "reassign"), ("reallocate", "reallocate"), ("delete", "delete_arin"), ("remove", "remove")],
    )
    @pytest.mark.parametrize("refused", [False, True], ids=["unreachable", "refused"])
    @patch("netbox_rir_manager.views.ARINBackend")
    def test_arin_failure_shows_error_and_logs(
        self, mock_backend_cls, admin_client, rir_network, rir_user_key, failure, action, refused
    ):
        from netbox_rir_manager.models import RIRSyncLog, RIRTicket

        failure = WRITE_FAILURES[failure]
        detail, log = failure.arrange(mock_backend_cls.from_rir_config.return_value, refused)

        response = admin_client.post(_action_url(action, rir_network), failure.data)

        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()
        assert _messages(response) == [("danger", detail)]  # NetBox tags error messages "danger"
        error = RIRSyncLog.objects.get(status="error")
        assert (error.operation, error.message, error.object_handle) == (*log, rir_network.handle)
        assert not RIRTicket.objects.exists()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reallocate_data_backend_refuses(self, mock_backend_cls, admin_client, rir_network, rir_user_key):
        """Data the backend cannot send to ARIN is shown as an error and logged, not a 500."""
        from netbox_rir_manager.backends.base import RIRDataError
        from netbox_rir_manager.models import RIRSyncLog, RIRTicket

        mock_backend_cls.from_rir_config.return_value.reallocate_network.side_effect = RIRDataError(
            "Invalid Net details for ARIN: version: Field required"
        )

        response = admin_client.post(_action_url("reallocate", rir_network), REALLOCATION)

        assert response.status_code == 302
        assert response.url == rir_network.get_absolute_url()
        assert not RIRTicket.objects.exists()
        assert _messages(response) == [("danger", "Invalid Net details for ARIN: version: Field required")]
        assert RIRSyncLog.objects.get(status="error").operation == "reallocate"


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


@pytest.mark.django_db
class TestPrefixReassignView:
    """A manual reassignment from a prefix submits exactly what the form says, now."""

    @pytest.fixture
    def setup(self, rir_user_key, prefix_under_parent):
        # The parent is deliberately not opted into auto_reassign: that flag gates only the automatic path.
        return prefix_under_parent(
            "198.51.100.0/24", "198.51.100.16/28", "NET-198-51-100-0-1", tenant_name="Tenant Name"
        )

    def _post(self, client, prefix, **fields):
        data = {"start_address": "198.51.100.16", "end_address": "198.51.100.31", **fields}
        return client.post(reverse("plugins:netbox_rir_manager:prefix_reassign", args=[prefix.pk]), data)

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_detailed_submits_form_values(self, mock_backend_cls, admin_client, setup):
        from netbox_rir_manager.models import RIRNetwork, RIRTicket

        mock_backend = MagicMock()
        mock_backend.reassign_network.return_value = {
            "ticket_number": "TKT-PFX-1",
            "ticket_status": "PENDING_REVIEW",
            "net": {"handle": "NET-198-51-100-16-1", "net_name": "TYPED-NAME", "raw_data": {}},
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        response = self._post(
            admin_client, setup["prefix"], reassignment_type="detailed", org_handle="CUST-ARIN", net_name="TYPED-NAME"
        )

        mock_backend.reassign_network.assert_called_once_with(
            "NET-198-51-100-0-1",
            {
                "net_name": "TYPED-NAME",
                "start_address": "198.51.100.16",
                "end_address": "198.51.100.31",
                "org_handle": "CUST-ARIN",
            },
        )
        ticket = RIRTicket.objects.get(ticket_number="TKT-PFX-1")
        assert response.status_code == 302
        assert response.url == ticket.get_absolute_url()
        assert RIRNetwork.objects.get(handle="NET-198-51-100-16-1").prefix == setup["prefix"]

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_simple_creates_customer_from_form(self, mock_backend_cls, admin_client, setup):
        from netbox_rir_manager.models import RIRCustomer

        mock_backend = MagicMock()
        mock_backend.create_customer.return_value = {"handle": "C0000001"}
        mock_backend.reassign_network.return_value = {"ticket_number": "TKT-PFX-2", "raw_data": {}}
        mock_backend_cls.from_rir_config.return_value = mock_backend

        self._post(
            admin_client,
            setup["prefix"],
            reassignment_type="simple",
            customer_name="Typed Customer",
            city="Montreal",
            country="CA",
        )

        customer_data = mock_backend.create_customer.call_args[0][1]
        assert customer_data["customer_name"] == "Typed Customer"
        assert mock_backend.reassign_network.call_args[0][1]["customer_handle"] == "C0000001"
        customer = RIRCustomer.objects.get(handle="C0000001")
        assert customer.tenant == setup["tenant"]
        assert customer.network == setup["parent"]

    @pytest.mark.parametrize(
        "customer_result, reassign_result, expected_log",
        [
            pytest.param(None, None, ("create", "customer"), id="customer-creation-fails"),
            pytest.param({"handle": "C0000002"}, None, ("reassign", "network"), id="arin-refuses-reassignment"),
        ],
    )
    @patch("netbox_rir_manager.views.ARINBackend")
    def test_failure_returns_to_prefix_and_logs(
        self, mock_backend_cls, admin_client, setup, customer_result, reassign_result, expected_log
    ):
        from netbox_rir_manager.models import RIRSyncLog, RIRTicket

        mock_backend = MagicMock()
        mock_backend.create_customer.return_value = customer_result
        mock_backend.reassign_network.return_value = reassign_result
        mock_backend_cls.from_rir_config.return_value = mock_backend

        response = self._post(
            admin_client, setup["prefix"], reassignment_type="simple", customer_name="Cust", city="Laval", country="CA"
        )

        assert response.status_code == 302
        assert response.url == setup["prefix"].get_absolute_url()
        assert not RIRTicket.objects.exists()
        error = RIRSyncLog.objects.get(status="error")
        assert (error.operation, error.object_type) == expected_log

    def test_form_prefills_customer_address_from_site(self, admin_client, setup):
        from dcim.models import Site

        from netbox_rir_manager.models import RIRAddress

        site = Site.objects.create(name="Site P", slug="site-p")
        RIRAddress.objects.create(site=site, street_address="1 Rue A", city="Montreal", country="CA")
        prefix = setup["prefix"]
        prefix.scope = site
        prefix.save()

        response = admin_client.get(reverse("plugins:netbox_rir_manager:prefix_reassign", args=[prefix.pk]))

        initial = response.context["form"].initial
        assert (initial["customer_name"], initial["street_address"], initial["city"], initial["country"]) == (
            "Tenant Name",
            "1 Rue A",
            "Montreal",
            "CA",
        )

    def test_form_prefills_arin_net_name(self, admin_client, setup):
        response = admin_client.get(reverse("plugins:netbox_rir_manager:prefix_reassign", args=[setup["prefix"].pk]))

        assert response.status_code == 200
        assert response.context["form"].initial["net_name"] == "TENANT-NAME-198-51-100-16-28"
        assert response.context["parent_network"] == setup["parent"]


@pytest.mark.django_db
@pytest.mark.usefixtures("rir_user_key")
class TestImmediateResultViews:
    """ARIN processes some writes immediately and returns no ticket."""

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_delete_arin_without_ticket_twice(self, mock_backend_cls, admin_client, networks):
        from netbox_rir_manager.models import RIRTicket

        mock_backend_cls.from_rir_config.return_value.delete_network.return_value = immediate_result()

        for network in networks:
            response = admin_client.post(_action_url("delete_arin", network))
            assert response.status_code == 302
            assert response.url == network.get_absolute_url()
            level, text = _messages(response)[-1]  # the first request's message is never displayed
            assert level == "success"
            assert "immediately" in text

        assert not RIRTicket.objects.exists()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_network_reassign_without_ticket(self, mock_backend_cls, admin_client, networks, rir_config):
        """A reassignment without a ticket works even with a legacy empty-number ticket in the database."""
        from django.utils import timezone

        from netbox_rir_manager.models import RIRNetwork, RIRTicket

        RIRTicket.objects.create(
            rir_config=rir_config,
            ticket_number="",
            ticket_type="IPV4_SIMPLE_REASSIGN",
            status="resolved",
            created_date=timezone.now(),
        )
        mock_backend_cls.from_rir_config.return_value.reassign_network.return_value = immediate_result("NET-CHILD-1")

        response = admin_client.post(_action_url("reassign", networks[0]), DETAILED)

        assert response.status_code == 302
        assert response.url == networks[0].get_absolute_url()
        assert RIRTicket.objects.count() == 1
        assert RIRNetwork.objects.filter(handle="NET-CHILD-1").exists()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_reallocate_without_ticket(self, mock_backend_cls, admin_client, networks):
        from netbox_rir_manager.models import RIRTicket

        mock_backend_cls.from_rir_config.return_value.reallocate_network.return_value = immediate_result()

        response = admin_client.post(_action_url("reallocate", networks[0]), REALLOCATION)

        assert response.status_code == 302
        assert response.url == networks[0].get_absolute_url()
        assert not RIRTicket.objects.exists()

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_prefix_reassign_without_ticket_returns_to_prefix(
        self, mock_backend_cls, admin_client, prefix_under_parent, rir_user_key
    ):
        from netbox_rir_manager.models import RIRNetwork, RIRTicket

        setup = prefix_under_parent("198.51.100.0/24", "198.51.100.16/28", "NET-198-51-100-0-1")
        mock_backend_cls.from_rir_config.return_value.reassign_network.return_value = immediate_result(
            "NET-198-51-100-16-1"
        )

        response = admin_client.post(
            reverse("plugins:netbox_rir_manager:prefix_reassign", args=[setup["prefix"].pk]),
            {**DETAILED, "start_address": "198.51.100.16", "end_address": "198.51.100.31"},
        )

        assert response.status_code == 302
        assert response.url == setup["prefix"].get_absolute_url()
        assert not RIRTicket.objects.exists()
        assert RIRNetwork.objects.get(handle="NET-198-51-100-16-1").prefix == setup["prefix"]

    @patch("netbox_rir_manager.views.ARINBackend")
    def test_recording_failure_warns_that_arin_changed(self, mock_backend_cls, admin_client, networks, rir_ticket):
        mock_backend_cls.from_rir_config.return_value.delete_network.return_value = ticket_result(EXISTING_TICKET)

        response = admin_client.post(_action_url("delete_arin", networks[0]))

        assert response.status_code == 302
        assert response.url == networks[0].get_absolute_url()
        [(level, text)] = _messages(response)
        assert level == "warning"
        assert "succeeded at ARIN" in text
