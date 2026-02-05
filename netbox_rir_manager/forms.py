from django import forms
from ipam.models import RIR
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from utilities.forms.rendering import FieldSet

from netbox_rir_manager.models import RIRConfig, RIRContact, RIRNetwork, RIROrganization


class RIRConfigForm(NetBoxModelForm):
    rir = DynamicModelChoiceField(queryset=RIR.objects.all())

    fieldsets = (
        FieldSet("rir", "name", "api_url", "org_handle", "is_active", name="RIR Config"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRConfig
        fields = ("rir", "name", "api_url", "org_handle", "is_active", "tags")


class RIRConfigFilterForm(NetBoxModelFilterSetForm):
    model = RIRConfig
    rir_id = DynamicModelMultipleChoiceField(queryset=RIR.objects.all(), required=False, label="RIR")
    is_active = forms.NullBooleanField(required=False)


class RIROrganizationForm(NetBoxModelForm):
    rir_config = DynamicModelChoiceField(queryset=RIRConfig.objects.all())

    fieldsets = (
        FieldSet("rir_config", "handle", "name", name="Organization"),
        FieldSet("street_address", "city", "state_province", "postal_code", "country", name="Address"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIROrganization
        fields = (
            "rir_config",
            "handle",
            "name",
            "street_address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "tags",
        )


class RIROrganizationFilterForm(NetBoxModelFilterSetForm):
    model = RIROrganization
    rir_config_id = DynamicModelMultipleChoiceField(
        queryset=RIRConfig.objects.all(), required=False, label="RIR Config"
    )
    country = forms.CharField(required=False)


class RIRContactForm(NetBoxModelForm):
    rir_config = DynamicModelChoiceField(queryset=RIRConfig.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)

    fieldsets = (
        FieldSet("rir_config", "handle", "contact_type", name="Contact"),
        FieldSet("first_name", "last_name", "company_name", "email", "phone", name="Details"),
        FieldSet("organization", name="Organization"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRContact
        fields = (
            "rir_config",
            "handle",
            "contact_type",
            "first_name",
            "last_name",
            "company_name",
            "email",
            "phone",
            "organization",
            "tags",
        )


class RIRContactFilterForm(NetBoxModelFilterSetForm):
    model = RIRContact
    rir_config_id = DynamicModelMultipleChoiceField(
        queryset=RIRConfig.objects.all(), required=False, label="RIR Config"
    )
    contact_type = forms.CharField(required=False)
    organization_id = DynamicModelMultipleChoiceField(
        queryset=RIROrganization.objects.all(), required=False, label="Organization"
    )


class RIRNetworkForm(NetBoxModelForm):
    rir_config = DynamicModelChoiceField(queryset=RIRConfig.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)

    fieldsets = (
        FieldSet("rir_config", "handle", "net_name", "organization", name="Network"),
        FieldSet("aggregate", "prefix", name="NetBox Links"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRNetwork
        fields = ("rir_config", "handle", "net_name", "organization", "aggregate", "prefix", "tags")


class RIRNetworkFilterForm(NetBoxModelFilterSetForm):
    model = RIRNetwork
    rir_config_id = DynamicModelMultipleChoiceField(
        queryset=RIRConfig.objects.all(), required=False, label="RIR Config"
    )
    organization_id = DynamicModelMultipleChoiceField(
        queryset=RIROrganization.objects.all(), required=False, label="Organization"
    )
