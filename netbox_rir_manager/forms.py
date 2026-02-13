from django import forms
from django.contrib.auth import get_user_model
from ipam.models import RIR
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from tenancy.models import Contact, Tenant
from utilities.forms.fields import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from utilities.forms.rendering import FieldSet

from netbox_rir_manager.models import (
    RIRConfig,
    RIRContact,
    RIRNetwork,
    RIROrganization,
    RIRSiteAddress,
    RIRTicket,
    RIRUserKey,
)


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
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)

    fieldsets = (
        FieldSet("rir_config", "handle", "name", "tenant", name="Organization"),
        FieldSet("street_address", "city", "state_province", "postal_code", "country", name="Address"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIROrganization
        fields = (
            "rir_config",
            "handle",
            "name",
            "tenant",
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
    tenant_id = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False, label="Tenant")
    country = forms.CharField(required=False)


class RIRContactForm(NetBoxModelForm):
    rir_config = DynamicModelChoiceField(queryset=RIRConfig.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)
    contact = DynamicModelChoiceField(queryset=Contact.objects.all(), required=False)

    fieldsets = (
        FieldSet("rir_config", "handle", "contact_type", name="Contact"),
        FieldSet("first_name", "last_name", "company_name", "email", "phone", name="Details"),
        FieldSet("street_address", "city", "state_province", "postal_code", "country", name="Address"),
        FieldSet("organization", "contact", name="Links"),
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
            "street_address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "organization",
            "contact",
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
    contact_id = DynamicModelMultipleChoiceField(queryset=Contact.objects.all(), required=False, label="Contact")


class RIRNetworkForm(NetBoxModelForm):
    rir_config = DynamicModelChoiceField(queryset=RIRConfig.objects.all())
    organization = DynamicModelChoiceField(queryset=RIROrganization.objects.all(), required=False)

    fieldsets = (
        FieldSet("rir_config", "handle", "net_name", "net_type", "organization", "auto_reassign", name="Network"),
        FieldSet("aggregate", "prefix", name="NetBox Links"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRNetwork
        fields = (
            "rir_config",
            "handle",
            "net_name",
            "net_type",
            "organization",
            "auto_reassign",
            "aggregate",
            "prefix",
            "tags",
        )


class RIRNetworkFilterForm(NetBoxModelFilterSetForm):
    model = RIRNetwork
    rir_config_id = DynamicModelMultipleChoiceField(
        queryset=RIRConfig.objects.all(), required=False, label="RIR Config"
    )
    organization_id = DynamicModelMultipleChoiceField(
        queryset=RIROrganization.objects.all(), required=False, label="Organization"
    )
    auto_reassign = forms.NullBooleanField(required=False)


class RIRSiteAddressForm(NetBoxModelForm):
    fieldsets = (
        FieldSet("site", name="Site"),
        FieldSet("street_address", "city", "state_province", "postal_code", "country", name="Address"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRSiteAddress
        fields = (
            "site",
            "street_address",
            "city",
            "state_province",
            "postal_code",
            "country",
            "tags",
        )


class RIRTicketFilterForm(NetBoxModelFilterSetForm):
    model = RIRTicket
    rir_config_id = DynamicModelMultipleChoiceField(
        queryset=RIRConfig.objects.all(), required=False, label="RIR Config"
    )
    status = forms.CharField(required=False)
    ticket_type = forms.CharField(required=False)


class RIRUserKeyForm(NetBoxModelForm):
    user = DynamicModelChoiceField(queryset=get_user_model().objects.all())
    rir_config = DynamicModelChoiceField(queryset=RIRConfig.objects.all())

    fieldsets = (
        FieldSet("user", "rir_config", "api_key", name="User Key"),
        FieldSet("tags", name="Tags"),
    )

    class Meta:
        model = RIRUserKey
        fields = ("user", "rir_config", "api_key", "tags")
        widgets = {
            "api_key": forms.PasswordInput(),
        }


class RIRUserKeyFilterForm(NetBoxModelFilterSetForm):
    model = RIRUserKey
    user = DynamicModelMultipleChoiceField(queryset=get_user_model().objects.all(), required=False, label="User")
    rir_config_id = DynamicModelMultipleChoiceField(
        queryset=RIRConfig.objects.all(), required=False, label="RIR Config"
    )


class RIRNetworkReassignForm(forms.Form):
    """Form for reassigning a network (simple or detailed)."""

    reassignment_type = forms.ChoiceField(
        choices=[("simple", "Simple Reassignment"), ("detailed", "Detailed Reassignment")],
        initial="simple",
    )
    # Simple reassignment fields (customer)
    customer_name = forms.CharField(max_length=255, required=False, help_text="Customer/recipient name")
    street_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    city = forms.CharField(max_length=100, required=False)
    state_province = forms.CharField(max_length=100, required=False)
    postal_code = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=2, required=False, help_text="ISO 3166-1 two-letter code")
    # Detailed reassignment fields
    org_handle = forms.CharField(
        max_length=50, required=False, help_text="Recipient ORG handle for detailed reassignment"
    )
    # Common fields
    net_name = forms.CharField(max_length=100, required=False, help_text="Name for the reassigned subnet")
    start_address = forms.GenericIPAddressField(help_text="Start IP of the subnet to reassign")
    end_address = forms.GenericIPAddressField(help_text="End IP of the subnet to reassign")

    def clean(self):
        cleaned = super().clean()
        rtype = cleaned.get("reassignment_type")
        if rtype == "simple":
            for field in ("customer_name", "city", "country"):
                if not cleaned.get(field):
                    self.add_error(field, "Required for simple reassignment.")
        elif rtype == "detailed" and not cleaned.get("org_handle"):
            self.add_error("org_handle", "Required for detailed reassignment.")
        return cleaned


class RIRNetworkReallocateForm(forms.Form):
    """Form for reallocating a network to an ORG."""

    org_handle = forms.CharField(max_length=50, help_text="Recipient ORG handle")
    net_name = forms.CharField(max_length=100, required=False, help_text="Name for the reallocated subnet")
    start_address = forms.GenericIPAddressField(help_text="Start IP of the subnet to reallocate")
    end_address = forms.GenericIPAddressField(help_text="End IP of the subnet to reallocate")
