from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from netbox_rir_manager.models import RIRAccount, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog


class RIRAccountSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:riraccount-detail")

    class Meta:
        model = RIRAccount
        fields = (
            "id",
            "url",
            "display",
            "rir",
            "name",
            "api_url",
            "org_handle",
            "is_active",
            "last_sync",
            "tags",
            "created",
            "last_updated",
        )
        # api_key is intentionally excluded for security


class RIROrganizationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rirorganization-detail")

    class Meta:
        model = RIROrganization
        fields = (
            "id",
            "url",
            "display",
            "account",
            "handle",
            "name",
            "street_address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "raw_data",
            "last_synced",
            "tags",
            "created",
            "last_updated",
        )


class RIRContactSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rircontact-detail")

    class Meta:
        model = RIRContact
        fields = (
            "id",
            "url",
            "display",
            "account",
            "handle",
            "contact_type",
            "first_name",
            "last_name",
            "company_name",
            "email",
            "phone",
            "organization",
            "raw_data",
            "last_synced",
            "tags",
            "created",
            "last_updated",
        )


class RIRNetworkSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rirnetwork-detail")

    class Meta:
        model = RIRNetwork
        fields = (
            "id",
            "url",
            "display",
            "account",
            "handle",
            "net_name",
            "organization",
            "aggregate",
            "prefix",
            "raw_data",
            "last_synced",
            "tags",
            "created",
            "last_updated",
        )


class RIRSyncLogSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rirsynclog-detail")

    class Meta:
        model = RIRSyncLog
        fields = (
            "id",
            "url",
            "display",
            "account",
            "operation",
            "object_type",
            "object_handle",
            "status",
            "message",
            "tags",
            "created",
            "last_updated",
        )
