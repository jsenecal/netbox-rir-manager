import django_filters
from django.contrib.auth import get_user_model
from django.db import models
from ipam.models import RIR
from netbox.filtersets import NetBoxModelFilterSet
from tenancy.models import Contact, Tenant

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


class RIRConfigFilterSet(NetBoxModelFilterSet):
    rir_id = django_filters.ModelMultipleChoiceFilter(queryset=RIR.objects.all(), label="RIR")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = RIRConfig
        fields = ("id", "name", "rir_id", "is_active", "org_handle")

    def search(self, queryset, name, value):
        return queryset.filter(name__icontains=value)


class RIROrganizationFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    tenant_id = django_filters.ModelMultipleChoiceFilter(queryset=Tenant.objects.all(), label="Tenant")
    country = django_filters.CharFilter(field_name="address__country")

    class Meta:
        model = RIROrganization
        fields = ("id", "handle", "name", "rir_config_id", "tenant_id")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(name__icontains=value)


class RIRCustomerFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    network_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRNetwork.objects.all(), label="Network")
    tenant_id = django_filters.ModelMultipleChoiceFilter(queryset=Tenant.objects.all(), label="Tenant")

    class Meta:
        model = RIRCustomer
        fields = ("id", "handle", "customer_name", "rir_config_id", "network_id", "tenant_id")

    def search(self, queryset, name, value):
        return queryset.filter(
            models.Q(handle__icontains=value) | models.Q(customer_name__icontains=value)
        )


class RIRContactFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    contact_type = django_filters.CharFilter()
    organization_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIROrganization.objects.all(), label="Organization"
    )
    contact_id = django_filters.ModelMultipleChoiceFilter(queryset=Contact.objects.all(), label="NetBox Contact")
    has_contact = django_filters.BooleanFilter(
        field_name="contact", lookup_expr="isnull", exclude=True, label="Has NetBox contact"
    )

    class Meta:
        model = RIRContact
        fields = ("id", "handle", "contact_type", "rir_config_id", "organization_id", "contact_id")

    def search(self, queryset, name, value):
        return queryset.filter(
            models.Q(handle__icontains=value)
            | models.Q(last_name__icontains=value)
            | models.Q(first_name__icontains=value)
            | models.Q(contact__name__icontains=value)
        )


class RIRNetworkFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    organization_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIROrganization.objects.all(), label="Organization"
    )
    net_type = django_filters.CharFilter()
    auto_reassign = django_filters.BooleanFilter()

    class Meta:
        model = RIRNetwork
        fields = ("id", "handle", "net_name", "net_type", "rir_config_id", "organization_id", "auto_reassign")

    def search(self, queryset, name, value):
        return queryset.filter(handle__icontains=value) | queryset.filter(net_name__icontains=value)


class RIRAddressFilterSet(NetBoxModelFilterSet):
    site_id = django_filters.NumberFilter(field_name="site__id")
    country = django_filters.CharFilter()
    auto_resolved = django_filters.BooleanFilter()

    class Meta:
        model = RIRAddress
        fields = ("id", "site_id", "country", "auto_resolved")

    def search(self, queryset, name, value):
        return queryset.filter(site__name__icontains=value) | queryset.filter(city__icontains=value)


class RIRSyncLogFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    operation = django_filters.CharFilter()
    status = django_filters.CharFilter()

    class Meta:
        model = RIRSyncLog
        fields = ("id", "rir_config_id", "operation", "status", "object_type")

    def search(self, queryset, name, value):
        return queryset.filter(object_handle__icontains=value) | queryset.filter(message__icontains=value)


class RIRTicketFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")
    status = django_filters.CharFilter()
    ticket_type = django_filters.CharFilter()
    network_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRNetwork.objects.all(), label="Network")

    class Meta:
        model = RIRTicket
        fields = ("id", "ticket_number", "ticket_type", "status", "rir_config_id", "network_id")

    def search(self, queryset, name, value):
        return queryset.filter(ticket_number__icontains=value)


class RIRUserKeyFilterSet(NetBoxModelFilterSet):
    user = django_filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all(), label="User")
    rir_config_id = django_filters.ModelMultipleChoiceFilter(queryset=RIRConfig.objects.all(), label="RIR Config")

    class Meta:
        model = RIRUserKey
        fields = ("id", "user", "rir_config_id")

    def search(self, queryset, name, value):
        return queryset.filter(user__username__icontains=value)
