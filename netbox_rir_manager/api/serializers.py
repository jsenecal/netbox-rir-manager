from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from netbox_rir_manager.models import RIRConfig, RIRContact, RIRNetwork, RIROrganization, RIRSyncLog, RIRUserKey


class RIRConfigSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rirconfig-detail")

    class Meta:
        model = RIRConfig
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


class RIROrganizationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rirorganization-detail")

    class Meta:
        model = RIROrganization
        fields = (
            "id",
            "url",
            "display",
            "rir_config",
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
            "rir_config",
            "handle",
            "contact_type",
            "first_name",
            "last_name",
            "company_name",
            "email",
            "phone",
            "organization",
            "contact",
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
            "rir_config",
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
            "rir_config",
            "operation",
            "object_type",
            "object_handle",
            "status",
            "message",
            "tags",
            "created",
            "last_updated",
        )


class RIRUserKeySerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:riruserkey-detail")
    api_key = serializers.CharField(write_only=True)

    class Meta:
        model = RIRUserKey
        fields = (
            "id",
            "url",
            "display",
            "user",
            "rir_config",
            "api_key",
            "tags",
            "created",
            "last_updated",
        )
