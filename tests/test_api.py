from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from tests.arin_payloads import (
    DETAILED,
    EXISTING_TICKET,
    REALLOCATION,
    WRITE_FAILURES,
    immediate_result,
    ticket_result,
)


@pytest.mark.django_db
class TestRIRConfigAPI:
    def test_list_configs(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirconfig-list")
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_config(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirconfig-detail", args=[rir_config.pk])
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == rir_config.name

    def test_create_config(self, admin_api_client, rir):
        url = reverse("plugins-api:netbox_rir_manager-api:rirconfig-list")
        data = {
            "rir": rir.pk,
            "name": "New API Config",
            "org_handle": "NEW-ARIN",
            "is_active": True,
        }
        response = admin_api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "New API Config"

    def test_update_config(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirconfig-detail", args=[rir_config.pk])
        response = admin_api_client.patch(url, {"name": "Updated Name"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Updated Name"

    def test_delete_config(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirconfig-detail", args=[rir_config.pk])
        response = admin_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_by_active(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirconfig-list")
        response = admin_api_client.get(url, {"is_active": "true"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = admin_api_client.get(url, {"is_active": "false"})
        assert response.json()["count"] == 0


@pytest.mark.django_db
class TestRIROrganizationAPI:
    def test_list_organizations(self, admin_api_client, rir_organization):
        url = reverse("plugins-api:netbox_rir_manager-api:rirorganization-list")
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_organization(self, admin_api_client, rir_organization):
        url = reverse("plugins-api:netbox_rir_manager-api:rirorganization-detail", args=[rir_organization.pk])
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["handle"] == rir_organization.handle

    def test_create_organization(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirorganization-list")
        data = {
            "rir_config": rir_config.pk,
            "handle": "NEWORG-ARIN",
            "name": "New Organization",
        }
        response = admin_api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["handle"] == "NEWORG-ARIN"

    def test_filter_by_rir_config(self, admin_api_client, rir_organization, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirorganization-list")
        response = admin_api_client.get(url, {"rir_config_id": rir_config.pk})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1


@pytest.mark.django_db
class TestRIRContactAPI:
    def test_list_contacts(self, admin_api_client, rir_contact):
        url = reverse("plugins-api:netbox_rir_manager-api:rircontact-list")
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_contact(self, admin_api_client, rir_contact):
        url = reverse("plugins-api:netbox_rir_manager-api:rircontact-detail", args=[rir_contact.pk])
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["handle"] == rir_contact.handle

    def test_create_contact(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rircontact-list")
        data = {
            "rir_config": rir_config.pk,
            "handle": "NEWPOC-ARIN",
            "contact_type": "ROLE",
            "last_name": "NOC",
            "email": "noc@example.com",
        }
        response = admin_api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["handle"] == "NEWPOC-ARIN"

    def test_filter_by_contact_type(self, admin_api_client, rir_contact):
        url = reverse("plugins-api:netbox_rir_manager-api:rircontact-list")
        response = admin_api_client.get(url, {"contact_type": "PERSON"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = admin_api_client.get(url, {"contact_type": "ROLE"})
        assert response.json()["count"] == 0


@pytest.mark.django_db
class TestRIRNetworkAPI:
    def test_list_networks(self, admin_api_client, rir_network):
        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-list")
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_network(self, admin_api_client, rir_network):
        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-detail", args=[rir_network.pk])
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["handle"] == rir_network.handle

    def test_create_network(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-list")
        data = {
            "rir_config": rir_config.pk,
            "handle": "NET-10-0-0-0-1",
            "net_name": "TEN-NET",
        }
        response = admin_api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["net_name"] == "TEN-NET"


@pytest.mark.django_db
class TestRIRSyncLogAPI:
    def test_list_sync_logs(self, admin_api_client, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="TEST", status="success"
        )
        url = reverse("plugins-api:netbox_rir_manager-api:rirsynclog-list")
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_sync_log(self, admin_api_client, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="TEST", status="success"
        )
        url = reverse("plugins-api:netbox_rir_manager-api:rirsynclog-detail", args=[log.pk])
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "success"

    def test_filter_by_status(self, admin_api_client, rir_config):
        from netbox_rir_manager.models import RIRSyncLog

        RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="A", status="success"
        )
        RIRSyncLog.objects.create(
            rir_config=rir_config, operation="sync", object_type="org", object_handle="B", status="error"
        )
        url = reverse("plugins-api:netbox_rir_manager-api:rirsynclog-list")
        response = admin_api_client.get(url, {"status": "success"})
        assert response.json()["count"] == 1
        response = admin_api_client.get(url, {"status": "error"})
        assert response.json()["count"] == 1


@pytest.mark.django_db
class TestRIRTicketAPI:
    def test_list_tickets(self, admin_api_client, rir_ticket):
        url = reverse("plugins-api:netbox_rir_manager-api:rirticket-list")
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_ticket(self, admin_api_client, rir_ticket):
        url = reverse("plugins-api:netbox_rir_manager-api:rirticket-detail", args=[rir_ticket.pk])
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ticket_number"] == rir_ticket.ticket_number

    def test_create_ticket(self, admin_api_client, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:rirticket-list")
        data = {
            "rir_config": rir_config.pk,
            "ticket_number": "TKT-API-001",
            "ticket_type": "IPV4_SIMPLE_REASSIGN",
            "status": "pending_review",
            "created_date": "2024-01-01T00:00:00Z",
        }
        response = admin_api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["ticket_number"] == "TKT-API-001"

    def test_filter_by_status(self, admin_api_client, rir_ticket):
        url = reverse("plugins-api:netbox_rir_manager-api:rirticket-list")
        response = admin_api_client.get(url, {"status": "pending_review"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

        response = admin_api_client.get(url, {"status": "resolved"})
        assert response.json()["count"] == 0


@pytest.mark.django_db
class TestRIRUserKeyAPI:
    def test_list_user_keys(self, admin_api_client, rir_user_key):
        url = reverse("plugins-api:netbox_rir_manager-api:riruserkey-list")
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_user_key(self, admin_api_client, rir_user_key):
        url = reverse("plugins-api:netbox_rir_manager-api:riruserkey-detail", args=[rir_user_key.pk])
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # api_key should NOT be in response (write-only)
        assert "api_key" not in response.json()

    def test_create_user_key(self, admin_api_client, admin_user, rir_config):
        url = reverse("plugins-api:netbox_rir_manager-api:riruserkey-list")
        data = {
            "user": admin_user.pk,
            "rir_config": rir_config.pk,
            "api_key": "new-api-key",
        }
        response = admin_api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestAPIAuthentication:
    def test_unauthenticated_request_rejected(self):
        from rest_framework.test import APIClient

        client = APIClient()
        url = reverse("plugins-api:netbox_rir_manager-api:rirconfig-list")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


def _action_url(action, network):
    return reverse(f"plugins-api:netbox_rir_manager-api:rirnetwork-{action}", args=[network.pk])


@pytest.mark.django_db
class TestRIRNetworkAPIActions:
    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reassign_api_simple(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        backend = mock_backend_cls.from_rir_config.return_value
        backend.create_customer.return_value = {"handle": "C-TEST"}
        backend.reassign_network.return_value = ticket_result("TKT-API-001", "IPV4_SIMPLE_REASSIGN")

        response = admin_api_client.post(
            _action_url("reassign", rir_network),
            {
                "reassignment_type": "simple",
                "customer_name": "Test Customer",
                "city": "Testville",
                "country": "US",
                "start_address": "10.0.0.0",
                "end_address": "10.0.0.255",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["ticket_number"] == "TKT-API-001"

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reassign_api_no_key(self, mock_backend_cls, admin_api_client, rir_network):
        response = admin_api_client.post(_action_url("reassign", rir_network), DETAILED, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reassign_api_customer_data_arin_cannot_accept(
        self, mock_backend_cls, admin_api_client, rir_network, rir_user_key
    ):
        """Customer data the backend refuses is a 400 and logged, not a 500 or 502."""
        from netbox_rir_manager.backends.base import RIRDataError
        from netbox_rir_manager.models import RIRSyncLog

        mock_backend = mock_backend_cls.from_rir_config.return_value
        mock_backend.create_customer.side_effect = RIRDataError(
            "Invalid Customer details for ARIN: iso3166_2: String should have at most 3 characters"
        )

        response = admin_api_client.post(
            _action_url("reassign", rir_network),
            {
                "reassignment_type": "simple",
                "customer_name": "Cust",
                "city": "Laval",
                "state_province": "Quebec",
                "country": "CA",
                "start_address": "192.0.2.0",
                "end_address": "192.0.2.15",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "iso3166_2" in response.json()["detail"]
        mock_backend.reassign_network.assert_not_called()
        error = RIRSyncLog.objects.get(status="error")
        assert (error.operation, error.object_type) == ("create", "customer")

    def test_reassign_api_invalid_data(self, admin_api_client, rir_network, rir_user_key):
        # Missing required fields: start_address, end_address
        response = admin_api_client.post(
            _action_url("reassign", rir_network), {"reassignment_type": "simple"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("action", ["reassign", "reallocate"])
    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_rejects_net_name_arin_would_refuse(
        self, mock_backend_cls, admin_api_client, rir_network, rir_user_key, action
    ):
        response = admin_api_client.post(
            _action_url(action, rir_network), {**DETAILED, "net_name": "Customer Inc.-192.0.2.0/28"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "net_name" in response.json()
        mock_backend_cls.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reallocate_api(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        backend = mock_backend_cls.from_rir_config.return_value
        backend.reallocate_network.return_value = ticket_result("TKT-API-REALLOC", "IPV4_REALLOCATE")

        response = admin_api_client.post(
            _action_url("reallocate", rir_network), {**REALLOCATION, "net_name": "REALLOC-NET"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        backend.reallocate_network.assert_called_once_with(
            rir_network.handle,
            {
                "org_handle": "TARGET-ORG",
                "net_name": "REALLOC-NET",
                "start_address": "192.0.2.0",
                "end_address": "192.0.2.15",
            },
        )
        assert RIRTicket.objects.get(ticket_number="TKT-API-REALLOC").ticket_type == "IPV4_REALLOCATE"

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reallocate_api_data_backend_refuses(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        """Data the backend cannot send to ARIN is a 400 and logged, not a 500 or 502."""
        from netbox_rir_manager.backends.base import RIRDataError
        from netbox_rir_manager.models import RIRSyncLog

        mock_backend = mock_backend_cls.from_rir_config.return_value
        mock_backend.reallocate_network.side_effect = RIRDataError(
            "Invalid Net details for ARIN: version: Field required"
        )

        response = admin_api_client.post(_action_url("reallocate", rir_network), REALLOCATION, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "version" in response.json()["detail"]
        error = RIRSyncLog.objects.get(status="error")
        assert (error.operation, error.object_type) == ("reallocate", "network")

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_remove_api(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        mock_backend_cls.from_rir_config.return_value.remove_network.return_value = True

        response = admin_api_client.post(_action_url("remove-net", rir_network), format="json")
        assert response.status_code == status.HTTP_200_OK

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_delete_arin_api(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        from netbox_rir_manager.models import RIRTicket

        backend = mock_backend_cls.from_rir_config.return_value
        backend.delete_network.return_value = ticket_result("TKT-API-DELETE", "NET_DELETE_REQUEST")

        response = admin_api_client.post(_action_url("delete-arin", rir_network), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        ticket = RIRTicket.objects.get(ticket_number="TKT-API-DELETE")
        assert response.json()["id"] == ticket.pk
        assert ticket.network == rir_network
        backend.delete_network.assert_called_once_with(rir_network.handle)

    @pytest.mark.parametrize(
        "failure, action",
        [("reassign", "reassign"), ("reallocate", "reallocate"), ("delete", "delete-arin"), ("remove", "remove-net")],
    )
    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_arin_failure_returns_502_and_logs(
        self, mock_backend_cls, admin_api_client, rir_network, rir_user_key, failure, action
    ):
        from netbox_rir_manager.models import RIRSyncLog, RIRTicket

        failure = WRITE_FAILURES[failure]
        getattr(mock_backend_cls.from_rir_config.return_value, failure.method).return_value = failure.returns

        response = admin_api_client.post(_action_url(action, rir_network), failure.data, format="json")

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.json()["detail"] == failure.detail
        error = RIRSyncLog.objects.get(status="error")
        assert (error.operation, error.message, error.object_handle) == (*failure.log, rir_network.handle)
        assert not RIRTicket.objects.exists()

    def test_ticket_refresh_api(self, admin_api_client, rir_ticket):
        url = reverse("plugins-api:netbox_rir_manager-api:rirticket-refresh", args=[rir_ticket.pk])
        response = admin_api_client.post(url, format="json")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.usefixtures("rir_user_key")
class TestAPIImmediateResults:
    """ARIN processes some writes immediately and returns no ticket."""

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_delete_arin_without_ticket_twice(self, mock_backend_cls, admin_api_client, networks):
        """Two immediate deletes in a row both succeed; no ticket with an empty number is stored."""
        from netbox_rir_manager.models import RIRSyncLog, RIRTicket

        mock_backend_cls.from_rir_config.return_value.delete_network.return_value = immediate_result()

        for network in networks:
            response = admin_api_client.post(_action_url("delete-arin", network), format="json")
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert body["ticket"] is None
            assert body["recorded"] is True
            assert "immediately" in body["detail"]

        assert not RIRTicket.objects.exists()
        logs = RIRSyncLog.objects.filter(operation="delete", status="success")
        assert sorted(logs.values_list("object_handle", flat=True)) == sorted(n.handle for n in networks)

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reassign_without_ticket_twice_returns_child_net(self, mock_backend_cls, admin_api_client, networks):
        from netbox_rir_manager.models import RIRNetwork, RIRTicket

        children = ["NET-CHILD-1", "NET-CHILD-2"]
        mock_backend_cls.from_rir_config.return_value.reassign_network.side_effect = [
            immediate_result(child) for child in children
        ]

        for network, child in zip(networks, children, strict=True):
            response = admin_api_client.post(_action_url("reassign", network), DETAILED, format="json")
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert body["ticket"] is None
            assert body["net"]["handle"] == child
            assert body["net"]["id"] == RIRNetwork.objects.get(handle=child).pk

        assert not RIRTicket.objects.exists()

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reallocate_without_ticket(self, mock_backend_cls, admin_api_client, networks):
        from netbox_rir_manager.models import RIRTicket

        mock_backend_cls.from_rir_config.return_value.reallocate_network.return_value = immediate_result()

        response = admin_api_client.post(_action_url("reallocate", networks[0]), REALLOCATION, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ticket"] is None
        assert not RIRTicket.objects.exists()

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_recording_failure_still_reports_arin_success(
        self, mock_backend_cls, admin_api_client, networks, rir_ticket
    ):
        """If NetBox cannot record a change ARIN already made, the caller still learns it happened."""
        from netbox_rir_manager.models import RIRSyncLog

        # ARIN hands back a ticket number NetBox already holds, so storing it fails.
        mock_backend_cls.from_rir_config.return_value.delete_network.return_value = ticket_result(EXISTING_TICKET)

        response = admin_api_client.post(_action_url("delete-arin", networks[0]), format="json")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["recorded"] is False
        assert body["ticket"] is None
        prefix = f"Delete request succeeded at ARIN (ticket {EXISTING_TICKET}), but NetBox could not record it."
        assert body["detail"].startswith(f"{prefix} Check the NetBox log. Error: duplicate key")
        assert "\n" not in body["detail"]
        error = RIRSyncLog.objects.get(operation="delete", status="error")
        assert error.object_handle == networks[0].handle
        assert error.message.startswith(f"{prefix} Error: duplicate key")
        assert "\n" not in error.message
        assert not RIRSyncLog.objects.filter(operation="delete", status="success").exists()
