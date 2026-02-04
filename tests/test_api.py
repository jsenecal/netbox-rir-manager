import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestRIRAccountAPI:
    def test_list_accounts(self, admin_client, rir_account):
        url = reverse("plugins-api:netbox_rir_manager-api:riraccount-list")
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    def test_get_account(self, admin_client, rir_account):
        url = reverse("plugins-api:netbox_rir_manager-api:riraccount-detail", args=[rir_account.pk])
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == rir_account.name

    def test_api_key_not_in_response(self, admin_client, rir_account):
        url = reverse("plugins-api:netbox_rir_manager-api:riraccount-detail", args=[rir_account.pk])
        response = admin_client.get(url)
        assert "api_key" not in response.json()
