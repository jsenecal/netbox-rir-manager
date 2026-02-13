from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from netbox_rir_manager.models import (
    RIRAddress,
    RIRConfig,
    RIRContact,
    RIRCustomer,
    RIRNetwork,
    RIROrganization,
    RIRSyncLog,
    RIRTicket,
    RIRUserKey,
)


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
            "tenant",
            "address",
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
            "address",
            "organization",
            "contact",
            "raw_data",
            "last_synced",
            "tags",
            "created",
            "last_updated",
        )


class RIRCustomerSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rircustomer-detail")

    class Meta:
        model = RIRCustomer
        fields = (
            "id",
            "url",
            "display",
            "rir_config",
            "handle",
            "customer_name",
            "address",
            "network",
            "tenant",
            "raw_data",
            "created_date",
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
            "net_type",
            "organization",
            "auto_reassign",
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


class RIRTicketSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:rirticket-detail")

    class Meta:
        model = RIRTicket
        fields = (
            "id",
            "url",
            "display",
            "rir_config",
            "ticket_number",
            "ticket_type",
            "status",
            "resolution",
            "network",
            "submitted_by",
            "created_date",
            "resolved_date",
            "raw_data",
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


class RIRAddressSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_rir_manager-api:riraddress-detail")

    class Meta:
        model = RIRAddress
        fields = (
            "id",
            "url",
            "display",
            "site",
            "street_address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "raw_geocode",
            "auto_resolved",
            "last_resolved",
            "tags",
            "created",
            "last_updated",
        )


class NetworkReassignSerializer(serializers.Serializer):
    reassignment_type = serializers.ChoiceField(choices=["simple", "detailed"])
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    street_address = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    country = serializers.CharField(max_length=2, required=False, allow_blank=True, default="")
    org_handle = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    net_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    start_address = serializers.IPAddressField()
    end_address = serializers.IPAddressField()

    def validate(self, data):
        rtype = data.get("reassignment_type")
        if rtype == "simple":
            for field in ("customer_name", "city", "country"):
                if not data.get(field):
                    raise serializers.ValidationError({field: "Required for simple reassignment."})
        elif rtype == "detailed" and not data.get("org_handle"):
            raise serializers.ValidationError({"org_handle": "Required for detailed reassignment."})
        return data


class NetworkReallocateSerializer(serializers.Serializer):
    org_handle = serializers.CharField(max_length=50)
    net_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    start_address = serializers.IPAddressField()
    end_address = serializers.IPAddressField()
