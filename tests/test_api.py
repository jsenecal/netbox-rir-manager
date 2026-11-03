import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status


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


@pytest.mark.django_db
class TestRIRNetworkAPIActions:
    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reassign_api_simple(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.create_customer.return_value = {"handle": "C-TEST"}
        mock_backend.reassign_network.return_value = {
            "ticket_number": "TKT-API-001",
            "ticket_type": "IPV4_SIMPLE_REASSIGN",
            "ticket_status": "PENDING_REVIEW",
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-reassign", args=[rir_network.pk])
        response = admin_api_client.post(
            url,
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
        assert "ticket_number" in response.json()

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reassign_api_no_key(self, mock_backend_cls, admin_api_client, rir_network):
        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-reassign", args=[rir_network.pk])
        response = admin_api_client.post(
            url,
            {
                "reassignment_type": "detailed",
                "org_handle": "TARGET-ORG",
                "start_address": "10.0.0.0",
                "end_address": "10.0.0.255",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reassign_api_arin_failure(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.reassign_network.return_value = None
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-reassign", args=[rir_network.pk])
        response = admin_api_client.post(
            url,
            {
                "reassignment_type": "detailed",
                "org_handle": "CUST-ARIN",
                "start_address": "192.0.2.0",
                "end_address": "192.0.2.15",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.json()["detail"] == "Reassignment failed at ARIN."

    def test_reassign_api_invalid_data(self, admin_api_client, rir_network, rir_user_key):
        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-reassign", args=[rir_network.pk])
        response = admin_api_client.post(
            url,
            {
                "reassignment_type": "simple",
                # Missing required fields: start_address, end_address
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("action", ["reassign", "reallocate"])
    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_rejects_net_name_arin_would_refuse(
        self, mock_backend_cls, admin_api_client, rir_network, rir_user_key, action
    ):
        url = reverse(f"plugins-api:netbox_rir_manager-api:rirnetwork-{action}", args=[rir_network.pk])
        response = admin_api_client.post(
            url,
            {
                "reassignment_type": "detailed",
                "org_handle": "CUST-ARIN",
                "net_name": "Customer Inc.-192.0.2.0/28",
                "start_address": "192.0.2.0",
                "end_address": "192.0.2.15",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "net_name" in response.json()
        mock_backend_cls.from_rir_config.assert_not_called()

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_reallocate_api(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.reallocate_network.return_value = {
            "ticket_number": "TKT-API-REALLOC",
            "ticket_type": "IPV4_REALLOCATE",
            "ticket_status": "PENDING_REVIEW",
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-reallocate", args=[rir_network.pk])
        response = admin_api_client.post(
            url,
            {
                "org_handle": "TARGET-ORG",
                "start_address": "10.0.0.0",
                "end_address": "10.0.0.255",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_remove_api(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.remove_network.return_value = True
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-remove-net", args=[rir_network.pk])
        response = admin_api_client.post(url, format="json")
        assert response.status_code == status.HTTP_200_OK

    @patch("netbox_rir_manager.api.views.ARINBackend")
    def test_delete_arin_api(self, mock_backend_cls, admin_api_client, rir_network, rir_user_key):
        mock_backend = MagicMock()
        mock_backend.delete_network.return_value = {
            "ticket_number": "TKT-API-DELETE",
            "ticket_type": "NET_DELETE_REQUEST",
            "ticket_status": "PENDING_REVIEW",
            "raw_data": {},
        }
        mock_backend_cls.from_rir_config.return_value = mock_backend

        url = reverse("plugins-api:netbox_rir_manager-api:rirnetwork-delete-arin", args=[rir_network.pk])
        response = admin_api_client.post(url, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_ticket_refresh_api(self, admin_api_client, rir_ticket):
        url = reverse("plugins-api:netbox_rir_manager-api:rirticket-refresh", args=[rir_ticket.pk])
        response = admin_api_client.post(url, format="json")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRIRConfigSyncAPI:
    """POST /configs/<pk>/sync/ queues a sync job for automation (issue #54)."""

    @staticmethod
    def _url(config):
        return reverse("plugins-api:netbox_rir_manager-api:rirconfig-sync", args=[config.pk])

    @patch("netbox_rir_manager.api.views.SyncRIRConfigJob")
    def test_queues_job_as_requester_and_returns_it(
        self, mock_job_cls, admin_api_client, admin_user, rir_config, rir_user_key
    ):
        from core.models import Job

        job = Job.objects.create(name="RIR Sync", object=rir_config, user=admin_user, job_id=uuid.uuid4())
        mock_job_cls.enqueue.return_value = job

        response = admin_api_client.post(self._url(rir_config), format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_job_cls.enqueue.assert_called_once_with(instance=rir_config, user=admin_user)
        body = response.json()
        assert body["id"] == job.pk
        assert body["url"].endswith(f"/api/core/jobs/{job.pk}/")

    @patch("netbox_rir_manager.api.views.SyncRIRConfigJob")
    def test_refuses_without_requesters_own_key(self, mock_job_cls, admin_api_client, rir_config, operator_key):
        rir_config.default_key = operator_key
        rir_config.save()

        response = admin_api_client.post(self._url(rir_config), format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "No API key configured for this RIR config."
        mock_job_cls.enqueue.assert_not_called()
