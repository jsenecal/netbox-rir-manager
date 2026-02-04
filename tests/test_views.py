import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestRIRAccountViews:
    def test_list_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:riraccount_list")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_view(self, admin_client, rir_account):
        url = reverse("plugins:netbox_rir_manager:riraccount", args=[rir_account.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_add_view(self, admin_client):
        url = reverse("plugins:netbox_rir_manager:riraccount_add")
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_edit_view(self, admin_client, rir_account):
        url = reverse("plugins:netbox_rir_manager:riraccount_edit", args=[rir_account.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_account):
        url = reverse("plugins:netbox_rir_manager:riraccount_delete", args=[rir_account.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_changelog_view(self, admin_client, rir_account):
        url = reverse("plugins:netbox_rir_manager:riraccount_changelog", args=[rir_account.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_list_view_with_data(self, admin_client, rir_account):
        url = reverse("plugins:netbox_rir_manager:riraccount_list")
        response = admin_client.get(url)
        assert response.status_code == 200
        assert rir_account.name.encode() in response.content


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

    def test_detail_view(self, admin_client, rir_account):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="TEST", status="success"
        )
        url = reverse("plugins:netbox_rir_manager:rirsynclog", args=[log.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_delete_view(self, admin_client, rir_account):
        from netbox_rir_manager.models import RIRSyncLog

        log = RIRSyncLog.objects.create(
            account=rir_account, operation="sync", object_type="org", object_handle="TEST", status="success"
        )
        url = reverse("plugins:netbox_rir_manager:rirsynclog_delete", args=[log.pk])
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestUnauthenticatedAccess:
    def test_list_view_requires_login(self):
        from django.test import Client

        client = Client()
        url = reverse("plugins:netbox_rir_manager:riraccount_list")
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login
