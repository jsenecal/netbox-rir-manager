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
            "city": "Springfield",
            "country": "US",
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
