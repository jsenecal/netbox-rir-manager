# NET Write Operations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ARIN network write operations (update, reassign, reallocate, remove, delete) with ticket tracking and action buttons on the RIRNetwork detail view.

**Architecture:** Extend `RIRBackend` with abstract write methods, implement in `ARINBackend` using pyregrws, add `RIRTicket` model for tracking ARIN ticket responses, create action views with forms on the RIRNetwork detail page, and expose write operations via REST API custom actions.

**Tech Stack:** pyregrws (Net, Customer, TicketRequest models), Django forms, NetBox generic views, DRF custom actions

---

### Task 1: Add RIRTicket Model and Choice Sets

**Files:**
- Modify: `netbox_rir_manager/choices.py`
- Create: `netbox_rir_manager/models/tickets.py`
- Modify: `netbox_rir_manager/models/__init__.py`

**Step 1: Add choice sets for ticket status, resolution, and type**

Add to `netbox_rir_manager/choices.py`:

```python
class TicketStatusChoices(ChoiceSet):
    key = "RIRTicket.status"

    CHOICES = [
        ("pending_confirmation", "Pending Confirmation", "cyan"),
        ("pending_review", "Pending Review", "blue"),
        ("assigned", "Assigned", "indigo"),
        ("in_progress", "In Progress", "yellow"),
        ("resolved", "Resolved", "green"),
        ("closed", "Closed", "gray"),
        ("approved", "Approved", "teal"),
    ]


class TicketResolutionChoices(ChoiceSet):
    key = "RIRTicket.resolution"

    CHOICES = [
        ("accepted", "Accepted", "green"),
        ("denied", "Denied", "red"),
        ("abandoned", "Abandoned", "gray"),
        ("processed", "Processed", "blue"),
        ("withdrawn", "Withdrawn", "orange"),
        ("other", "Other", "gray"),
    ]


class TicketTypeChoices(ChoiceSet):
    key = "RIRTicket.ticket_type"

    CHOICES = [
        ("IPV4_SIMPLE_REASSIGN", "IPv4 Simple Reassign", "blue"),
        ("IPV4_DETAILED_REASSIGN", "IPv4 Detailed Reassign", "indigo"),
        ("IPV4_REALLOCATE", "IPv4 Reallocate", "purple"),
        ("IPV6_DETAILED_REASSIGN", "IPv6 Detailed Reassign", "indigo"),
        ("IPV6_REALLOCATE", "IPv6 Reallocate", "purple"),
        ("NET_DELETE_REQUEST", "NET Delete Request", "red"),
    ]
```

**Step 2: Create the RIRTicket model**

Create `netbox_rir_manager/models/tickets.py`:

```python
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel

from netbox_rir_manager.choices import TicketResolutionChoices, TicketStatusChoices, TicketTypeChoices


class RIRTicket(NetBoxModel):
    """Tracks ARIN ticket requests from write operations."""

    rir_config = models.ForeignKey(
        "netbox_rir_manager.RIRConfig",
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    ticket_number = models.CharField(max_length=50, unique=True)
    ticket_type = models.CharField(max_length=50, choices=TicketTypeChoices)
    status = models.CharField(max_length=30, choices=TicketStatusChoices)
    resolution = models.CharField(
        max_length=30, choices=TicketResolutionChoices, blank=True, default=""
    )
    network = models.ForeignKey(
        "netbox_rir_manager.RIRNetwork",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    submitted_by = models.ForeignKey(
        "netbox_rir_manager.RIRUserKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    created_date = models.DateTimeField()
    resolved_date = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"Ticket {self.ticket_number}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_rir_manager:rirticket", args=[self.pk])
```

**Step 3: Export the model**

Add to `netbox_rir_manager/models/__init__.py`:

```python
from netbox_rir_manager.models.tickets import RIRTicket
```

And add `"RIRTicket"` to `__all__`.

**Step 4: Generate migration**

Run: `python manage.py makemigrations netbox_rir_manager`
Expected: New migration `0006_rirticket.py`

**Step 5: Write tests for RIRTicket model**

Add to `netbox_rir_manager/tests/test_models.py`:

```python
class RIRTicketModelTest(TestCase):
    def setUp(self):
        # Reuse existing setUp pattern for rir_config, user, user_key
        ...

    def test_create_ticket(self):
        ticket = RIRTicket.objects.create(
            rir_config=self.rir_config,
            ticket_number="TKT-20260205-001",
            ticket_type="IPV4_SIMPLE_REASSIGN",
            status="pending_review",
            network=self.network,
            submitted_by=self.user_key,
            created_date=timezone.now(),
        )
        assert str(ticket) == "Ticket TKT-20260205-001"
        assert ticket.get_absolute_url() == f"/plugins/rir-manager/tickets/{ticket.pk}/"

    def test_ticket_number_unique(self):
        RIRTicket.objects.create(
            rir_config=self.rir_config,
            ticket_number="TKT-UNIQUE",
            ticket_type="NET_DELETE_REQUEST",
            status="pending_review",
            created_date=timezone.now(),
        )
        with pytest.raises(IntegrityError):
            RIRTicket.objects.create(
                rir_config=self.rir_config,
                ticket_number="TKT-UNIQUE",
                ticket_type="NET_DELETE_REQUEST",
                status="pending_review",
                created_date=timezone.now(),
            )
```

**Step 6: Run tests to verify they pass**

Run: `python -m pytest netbox_rir_manager/tests/test_models.py -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add netbox_rir_manager/choices.py netbox_rir_manager/models/tickets.py \
  netbox_rir_manager/models/__init__.py netbox_rir_manager/migrations/0006_*.py \
  netbox_rir_manager/tests/test_models.py
git commit -m "feat: add RIRTicket model with status/resolution/type choices"
```

---

### Task 2: Add Backend Write Methods

**Files:**
- Modify: `netbox_rir_manager/backends/base.py`
- Modify: `netbox_rir_manager/backends/arin.py`
- Modify: `netbox_rir_manager/tests/test_backends/test_arin.py`
- Modify: `netbox_rir_manager/tests/test_backends/test_base.py`

**Step 1: Add abstract write methods to RIRBackend**

Add to `netbox_rir_manager/backends/base.py` (after `sync_resources`):

```python
@abstractmethod
def update_network(self, handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a network's details (name, POC links, comments). Returns updated net dict or None."""

@abstractmethod
def reassign_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
    """Reassign a subnet from parent NET. Returns ticket info dict or None."""

@abstractmethod
def reallocate_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
    """Reallocate a subnet from parent NET. Returns ticket info dict or None."""

@abstractmethod
def remove_network(self, handle: str) -> bool:
    """Remove a reassigned/reallocated network. Returns True on success."""

@abstractmethod
def delete_network(self, handle: str) -> dict[str, Any] | None:
    """Delete a network. Returns ticket info dict or None."""

@abstractmethod
def create_customer(self, parent_net_handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Create a customer under a parent NET for simple reassignment. Returns customer dict or None."""
```

**Step 2: Implement write methods in ARINBackend**

Add to `netbox_rir_manager/backends/arin.py`:

```python
def update_network(self, handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
    net = self._call_with_retry(self.api.net.from_handle, handle)
    if net is None or isinstance(net, Error):
        return None
    if "net_name" in data:
        net.net_name = data["net_name"]
    result = self._call_with_retry(net.save)
    if result is None or isinstance(result, Error):
        return None
    return self._net_to_dict(result)

def reassign_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
    parent = self._call_with_retry(self.api.net.from_handle, parent_handle)
    if parent is None or isinstance(parent, Error):
        return None
    from regrws.models import Net
    child_net = Net(**net_data)
    result = self._call_with_retry(self.api.net.reassign, parent, child_net)
    if result is None or isinstance(result, Error):
        return None
    return self._ticket_request_to_dict(result)

def reallocate_network(self, parent_handle: str, net_data: dict[str, Any]) -> dict[str, Any] | None:
    parent = self._call_with_retry(self.api.net.from_handle, parent_handle)
    if parent is None or isinstance(parent, Error):
        return None
    from regrws.models import Net
    child_net = Net(**net_data)
    result = self._call_with_retry(self.api.net.reallocate, parent, child_net)
    if result is None or isinstance(result, Error):
        return None
    return self._ticket_request_to_dict(result)

def remove_network(self, handle: str) -> bool:
    net = self._call_with_retry(self.api.net.from_handle, handle)
    if net is None or isinstance(net, Error):
        return False
    result = self._call_with_retry(self.api.net.remove, net)
    return not (result is None or isinstance(result, Error))

def delete_network(self, handle: str) -> dict[str, Any] | None:
    net = self._call_with_retry(self.api.net.from_handle, handle)
    if net is None or isinstance(net, Error):
        return None
    result = self._call_with_retry(net.delete)
    if result is None or isinstance(result, Error):
        return None
    return self._ticket_request_to_dict(result)

def create_customer(self, parent_net_handle: str, data: dict[str, Any]) -> dict[str, Any] | None:
    parent = self._call_with_retry(self.api.net.from_handle, parent_net_handle)
    if parent is None or isinstance(parent, Error):
        return None
    result = self._call_with_retry(self.api.customer.create_for_net, parent, **data)
    if result is None or isinstance(result, Error):
        return None
    return self._customer_to_dict(result)
```

**Step 3: Add helper methods for new data conversions**

Add to `ARINBackend`:

```python
def _ticket_request_to_dict(self, ticket_request: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    ticket = getattr(ticket_request, "ticket", None)
    if ticket:
        result["ticket_number"] = getattr(ticket, "ticket_no", "")
        result["ticket_status"] = getattr(ticket, "web_ticket_status", "")
        result["ticket_type"] = getattr(ticket, "web_ticket_type", "")
        result["ticket_resolution"] = getattr(ticket, "web_ticket_resolution", "")
        result["created_date"] = getattr(ticket, "created_date", "")
        result["resolved_date"] = getattr(ticket, "resolved_date", "")
        result["raw_data"] = self._safe_serialize(ticket)
    net = getattr(ticket_request, "net", None)
    if net:
        result["net"] = self._net_to_dict(net)
    return result

def _customer_to_dict(self, customer: Any) -> dict[str, Any]:
    return {
        "handle": getattr(customer, "handle", ""),
        "customer_name": getattr(customer, "customer_name", ""),
        "parent_org_handle": getattr(customer, "parent_org_handle", ""),
        "raw_data": self._safe_serialize(customer),
    }
```

**Step 4: Write tests for backend write methods**

Add tests to `netbox_rir_manager/tests/test_backends/test_arin.py` that mock pyregrws API calls and verify the backend methods return correct dicts or None on errors. Test each of the 6 write methods with both success and error cases (Error response, None response).

**Step 5: Update base backend tests**

Update `test_base.py` to verify the new abstract methods exist and that a concrete subclass must implement them.

**Step 6: Run tests**

Run: `python -m pytest netbox_rir_manager/tests/test_backends/ -v`
Expected: All tests pass

**Step 7: Commit**

```bash
git add netbox_rir_manager/backends/base.py netbox_rir_manager/backends/arin.py \
  netbox_rir_manager/tests/test_backends/
git commit -m "feat: add write methods to RIRBackend and ARINBackend"
```

---

### Task 3: Add RIRTicket Full Stack (Table, FilterSet, Form, Serializer, Views, URLs)

**Files:**
- Modify: `netbox_rir_manager/tables.py`
- Modify: `netbox_rir_manager/filtersets.py`
- Modify: `netbox_rir_manager/forms.py`
- Modify: `netbox_rir_manager/api/serializers.py`
- Modify: `netbox_rir_manager/api/views.py`
- Modify: `netbox_rir_manager/api/urls.py`
- Modify: `netbox_rir_manager/views.py`
- Modify: `netbox_rir_manager/urls.py`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rirticket.html`
- Modify: `netbox_rir_manager/navigation.py`
- Modify: `netbox_rir_manager/search.py`

**Step 1: Add RIRTicketTable**

Add to `netbox_rir_manager/tables.py`:

```python
from netbox_rir_manager.models import ..., RIRTicket

class RIRTicketTable(NetBoxTable):
    ticket_number = tables.Column(linkify=True)
    ticket_type = tables.Column()
    status = tables.Column()
    resolution = tables.Column()
    rir_config = tables.Column(linkify=True)
    network = tables.Column(linkify=True)
    created_date = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RIRTicket
        fields = (
            "pk", "id", "ticket_number", "ticket_type", "status", "resolution",
            "rir_config", "network", "created_date",
        )
        default_columns = (
            "ticket_number", "ticket_type", "status", "rir_config", "network", "created_date",
        )
```

**Step 2: Add RIRTicketFilterSet**

Add to `netbox_rir_manager/filtersets.py`:

```python
from netbox_rir_manager.models import ..., RIRTicket

class RIRTicketFilterSet(NetBoxModelFilterSet):
    rir_config_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIRConfig.objects.all(), label="RIR Config"
    )
    status = django_filters.CharFilter()
    ticket_type = django_filters.CharFilter()
    network_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIRNetwork.objects.all(), label="Network"
    )

    class Meta:
        model = RIRTicket
        fields = ("id", "ticket_number", "ticket_type", "status", "rir_config_id", "network_id")

    def search(self, queryset, name, value):
        return queryset.filter(ticket_number__icontains=value)
```

**Step 3: Add RIRTicketFilterForm**

Add to `netbox_rir_manager/forms.py`:

```python
from netbox_rir_manager.models import ..., RIRTicket

class RIRTicketFilterForm(NetBoxModelFilterSetForm):
    model = RIRTicket
    rir_config_id = DynamicModelMultipleChoiceField(
        queryset=RIRConfig.objects.all(), required=False, label="RIR Config"
    )
    status = forms.CharField(required=False)
    ticket_type = forms.CharField(required=False)
```

**Step 4: Add RIRTicketSerializer**

Add to `netbox_rir_manager/api/serializers.py`:

```python
from netbox_rir_manager.models import ..., RIRTicket

class RIRTicketSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_rir_manager-api:rirticket-detail"
    )

    class Meta:
        model = RIRTicket
        fields = (
            "id", "url", "display", "rir_config", "ticket_number", "ticket_type",
            "status", "resolution", "network", "submitted_by", "created_date",
            "resolved_date", "raw_data", "tags", "created", "last_updated",
        )
```

**Step 5: Add RIRTicketViewSet**

Add to `netbox_rir_manager/api/views.py`:

```python
from netbox_rir_manager.api.serializers import ..., RIRTicketSerializer
from netbox_rir_manager.filtersets import ..., RIRTicketFilterSet
from netbox_rir_manager.models import ..., RIRTicket

class RIRTicketViewSet(NetBoxModelViewSet):
    queryset = RIRTicket.objects.prefetch_related("tags")
    serializer_class = RIRTicketSerializer
    filterset_class = RIRTicketFilterSet
```

Register in `netbox_rir_manager/api/urls.py`:

```python
router.register("tickets", views.RIRTicketViewSet)
```

**Step 6: Add Django views**

Add to `netbox_rir_manager/views.py`:

```python
from netbox_rir_manager.models import ..., RIRTicket
from netbox_rir_manager.tables import ..., RIRTicketTable
from netbox_rir_manager.filtersets import ..., RIRTicketFilterSet
from netbox_rir_manager.forms import ..., RIRTicketFilterForm

class RIRTicketListView(generic.ObjectListView):
    queryset = RIRTicket.objects.all()
    table = RIRTicketTable
    filterset = RIRTicketFilterSet
    filterset_form = RIRTicketFilterForm

class RIRTicketView(generic.ObjectView):
    queryset = RIRTicket.objects.all()

class RIRTicketDeleteView(generic.ObjectDeleteView):
    queryset = RIRTicket.objects.all()
```

**Step 7: Add URL patterns**

Add to `netbox_rir_manager/urls.py`:

```python
from netbox_rir_manager.models import ..., RIRTicket

# RIRTicket
path("tickets/", views.RIRTicketListView.as_view(), name="rirticket_list"),
path("tickets/<int:pk>/", views.RIRTicketView.as_view(), name="rirticket"),
path("tickets/<int:pk>/delete/", views.RIRTicketDeleteView.as_view(), name="rirticket_delete"),
path("tickets/<int:pk>/changelog/", ObjectChangeLogView.as_view(), name="rirticket_changelog", kwargs={"model": RIRTicket}),
```

**Step 8: Create detail template**

Create `netbox_rir_manager/templates/netbox_rir_manager/rirticket.html`:

```html
{% extends 'generic/object.html' %}
{% load helpers %}
{% load plugins %}

{% block content %}
<div class="row mb-3">
    <div class="col col-md-6">
        <div class="card">
            <h5 class="card-header">Ticket</h5>
            <table class="table table-hover attr-table">
                <tr><th scope="row">RIR Config</th><td>{{ object.rir_config|linkify }}</td></tr>
                <tr><th scope="row">Ticket Number</th><td>{{ object.ticket_number }}</td></tr>
                <tr><th scope="row">Type</th><td>{{ object.get_ticket_type_display }}</td></tr>
                <tr><th scope="row">Status</th><td>{{ object.get_status_display }}</td></tr>
                <tr><th scope="row">Resolution</th><td>{{ object.get_resolution_display|placeholder }}</td></tr>
                <tr><th scope="row">Network</th><td>{{ object.network|linkify|placeholder }}</td></tr>
                <tr><th scope="row">Submitted By</th><td>{{ object.submitted_by|linkify|placeholder }}</td></tr>
                <tr><th scope="row">Created Date</th><td>{{ object.created_date }}</td></tr>
                <tr><th scope="row">Resolved Date</th><td>{{ object.resolved_date|placeholder }}</td></tr>
            </table>
        </div>
        {% plugin_left_page object %}
    </div>
    <div class="col col-md-6">
        {% include 'inc/panels/tags.html' %}
        {% plugin_right_page object %}
    </div>
</div>
{% endblock content %}
```

**Step 9: Add to navigation menu**

In `netbox_rir_manager/navigation.py`, add to the "Operations" group:

```python
PluginMenuItem(
    link="plugins:netbox_rir_manager:rirticket_list",
    link_text="Tickets",
    permissions=["netbox_rir_manager.view_rirticket"],
),
```

**Step 10: Add search index**

Add to `netbox_rir_manager/search.py`:

```python
from netbox_rir_manager.models import ..., RIRTicket

@register_search
class RIRTicketIndex(SearchIndex):
    model = RIRTicket
    fields = (
        ("ticket_number", 100),
    )
```

**Step 11: Write tests**

Add tests for:
- RIRTicketTable renders correctly
- RIRTicketFilterSet filters by status, type, config
- RIRTicketSerializer serializes correctly
- RIRTicket list/detail views return 200
- RIRTicket API list/detail return 200

**Step 12: Run tests**

Run: `python -m pytest netbox_rir_manager/tests/ -v`
Expected: All tests pass

**Step 13: Commit**

```bash
git add netbox_rir_manager/tables.py netbox_rir_manager/filtersets.py \
  netbox_rir_manager/forms.py netbox_rir_manager/api/ netbox_rir_manager/views.py \
  netbox_rir_manager/urls.py netbox_rir_manager/navigation.py netbox_rir_manager/search.py \
  netbox_rir_manager/templates/netbox_rir_manager/rirticket.html \
  netbox_rir_manager/tests/
git commit -m "feat: add RIRTicket full stack (views, API, table, filters, template)"
```

---

### Task 4: Add Network Write Action Views and Forms

**Files:**
- Modify: `netbox_rir_manager/forms.py`
- Modify: `netbox_rir_manager/views.py`
- Modify: `netbox_rir_manager/urls.py`
- Modify: `netbox_rir_manager/templates/netbox_rir_manager/rirnetwork.html`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rirnetwork_reassign.html`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rirnetwork_reallocate.html`
- Create: `netbox_rir_manager/templates/netbox_rir_manager/rirnetwork_confirm_action.html`

**Step 1: Add write operation forms**

Add to `netbox_rir_manager/forms.py`:

```python
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
    org_handle = forms.CharField(max_length=50, required=False, help_text="Recipient ORG handle for detailed reassignment")
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
        elif rtype == "detailed":
            if not cleaned.get("org_handle"):
                self.add_error("org_handle", "Required for detailed reassignment.")
        return cleaned


class RIRNetworkReallocateForm(forms.Form):
    """Form for reallocating a network to an ORG."""
    org_handle = forms.CharField(max_length=50, help_text="Recipient ORG handle")
    net_name = forms.CharField(max_length=100, required=False, help_text="Name for the reallocated subnet")
    start_address = forms.GenericIPAddressField(help_text="Start IP of the subnet to reallocate")
    end_address = forms.GenericIPAddressField(help_text="End IP of the subnet to reallocate")
```

**Step 2: Add action views**

Add to `netbox_rir_manager/views.py`:

```python
class RIRNetworkReassignView(LoginRequiredMixin, View):
    """Reassign a subnet from this network."""

    def get(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReassignForm()
        return render(request, "netbox_rir_manager/rirnetwork_reassign.html", {
            "object": network,
            "form": form,
        })

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReassignForm(request.POST)
        if not form.is_valid():
            return render(request, "netbox_rir_manager/rirnetwork_reassign.html", {
                "object": network,
                "form": form,
            })

        user_key = RIRUserKey.objects.filter(
            user=request.user, rir_config=network.rir_config
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)

        rtype = form.cleaned_data["reassignment_type"]
        if rtype == "simple":
            # Step 1: Create customer
            customer_data = {
                "customer_name": form.cleaned_data["customer_name"],
                "street_address": form.cleaned_data.get("street_address", ""),
                "city": form.cleaned_data["city"],
                "state_province": form.cleaned_data.get("state_province", ""),
                "postal_code": form.cleaned_data.get("postal_code", ""),
                "country": form.cleaned_data["country"],
            }
            customer_result = backend.create_customer(network.handle, customer_data)
            if customer_result is None:
                messages.error(request, "Failed to create customer at ARIN.")
                RIRSyncLog.objects.create(
                    rir_config=network.rir_config, operation="create",
                    object_type="customer", object_handle=network.handle,
                    status="error", message="Failed to create customer",
                )
                return redirect(network.get_absolute_url())

        # Step 2: Build NET payload and reassign
        net_data = {
            "net_name": form.cleaned_data.get("net_name", ""),
            "start_address": form.cleaned_data["start_address"],
            "end_address": form.cleaned_data["end_address"],
        }
        if rtype == "simple":
            net_data["customer_handle"] = customer_result["handle"]
        else:
            net_data["org_handle"] = form.cleaned_data["org_handle"]

        result = backend.reassign_network(network.handle, net_data)
        if result is None:
            messages.error(request, "Reassignment failed at ARIN.")
            RIRSyncLog.objects.create(
                rir_config=network.rir_config, operation="create",
                object_type="network", object_handle=network.handle,
                status="error", message="Reassignment failed",
            )
            return redirect(network.get_absolute_url())

        # Create ticket record
        ticket = RIRTicket.objects.create(
            rir_config=network.rir_config,
            ticket_number=result.get("ticket_number", ""),
            ticket_type=result.get("ticket_type", "IPV4_SIMPLE_REASSIGN"),
            status=_normalize_status(result.get("ticket_status", "")),
            network=network,
            submitted_by=user_key,
            created_date=timezone.now(),
            raw_data=result.get("raw_data", {}),
        )
        RIRSyncLog.objects.create(
            rir_config=network.rir_config, operation="create",
            object_type="network", object_handle=network.handle,
            status="success",
            message=f"Reassignment submitted, ticket {ticket.ticket_number}",
        )
        messages.success(request, f"Reassignment submitted. Ticket: {ticket.ticket_number}")
        return redirect(ticket.get_absolute_url())


class RIRNetworkReallocateView(LoginRequiredMixin, View):
    """Reallocate a subnet from this network."""

    def get(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReallocateForm()
        return render(request, "netbox_rir_manager/rirnetwork_reallocate.html", {
            "object": network,
            "form": form,
        })

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        form = RIRNetworkReallocateForm(request.POST)
        if not form.is_valid():
            return render(request, "netbox_rir_manager/rirnetwork_reallocate.html", {
                "object": network,
                "form": form,
            })

        user_key = RIRUserKey.objects.filter(
            user=request.user, rir_config=network.rir_config
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        net_data = {
            "org_handle": form.cleaned_data["org_handle"],
            "net_name": form.cleaned_data.get("net_name", ""),
            "start_address": form.cleaned_data["start_address"],
            "end_address": form.cleaned_data["end_address"],
        }
        result = backend.reallocate_network(network.handle, net_data)
        if result is None:
            messages.error(request, "Reallocation failed at ARIN.")
            RIRSyncLog.objects.create(
                rir_config=network.rir_config, operation="create",
                object_type="network", object_handle=network.handle,
                status="error", message="Reallocation failed",
            )
            return redirect(network.get_absolute_url())

        ticket = RIRTicket.objects.create(
            rir_config=network.rir_config,
            ticket_number=result.get("ticket_number", ""),
            ticket_type=result.get("ticket_type", "IPV4_REALLOCATE"),
            status=_normalize_status(result.get("ticket_status", "")),
            network=network,
            submitted_by=user_key,
            created_date=timezone.now(),
            raw_data=result.get("raw_data", {}),
        )
        RIRSyncLog.objects.create(
            rir_config=network.rir_config, operation="create",
            object_type="network", object_handle=network.handle,
            status="success",
            message=f"Reallocation submitted, ticket {ticket.ticket_number}",
        )
        messages.success(request, f"Reallocation submitted. Ticket: {ticket.ticket_number}")
        return redirect(ticket.get_absolute_url())


class RIRNetworkRemoveView(LoginRequiredMixin, View):
    """Remove a reassigned/reallocated network from ARIN."""

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        user_key = RIRUserKey.objects.filter(
            user=request.user, rir_config=network.rir_config
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        success = backend.remove_network(network.handle)
        if success:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config, operation="delete",
                object_type="network", object_handle=network.handle,
                status="success", message=f"Removed network {network.handle} from ARIN",
            )
            messages.success(request, f"Network {network.handle} removed from ARIN.")
        else:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config, operation="delete",
                object_type="network", object_handle=network.handle,
                status="error", message="Failed to remove network from ARIN",
            )
            messages.error(request, "Failed to remove network from ARIN.")
        return redirect(network.get_absolute_url())


class RIRNetworkDeleteARINView(LoginRequiredMixin, View):
    """Delete a network at ARIN (creates a ticket)."""

    def post(self, request, pk):
        network = get_object_or_404(RIRNetwork, pk=pk)
        user_key = RIRUserKey.objects.filter(
            user=request.user, rir_config=network.rir_config
        ).first()
        if not user_key:
            messages.error(request, "No API key configured for this RIR config.")
            return redirect(network.get_absolute_url())

        backend = ARINBackend.from_rir_config(network.rir_config, api_key=user_key.api_key)
        result = backend.delete_network(network.handle)
        if result is None:
            RIRSyncLog.objects.create(
                rir_config=network.rir_config, operation="delete",
                object_type="network", object_handle=network.handle,
                status="error", message="Failed to delete network at ARIN",
            )
            messages.error(request, "Failed to delete network at ARIN.")
            return redirect(network.get_absolute_url())

        ticket = RIRTicket.objects.create(
            rir_config=network.rir_config,
            ticket_number=result.get("ticket_number", ""),
            ticket_type="NET_DELETE_REQUEST",
            status=_normalize_status(result.get("ticket_status", "")),
            network=network,
            submitted_by=user_key,
            created_date=timezone.now(),
            raw_data=result.get("raw_data", {}),
        )
        RIRSyncLog.objects.create(
            rir_config=network.rir_config, operation="delete",
            object_type="network", object_handle=network.handle,
            status="success",
            message=f"Delete request submitted, ticket {ticket.ticket_number}",
        )
        messages.success(request, f"Delete request submitted. Ticket: {ticket.ticket_number}")
        return redirect(ticket.get_absolute_url())
```

Add helper function to `views.py`:

```python
def _normalize_status(arin_status: str) -> str:
    """Map ARIN ticket status strings to our TicketStatusChoices values."""
    mapping = {
        "PENDING_CONFIRMATION": "pending_confirmation",
        "PENDING_REVIEW": "pending_review",
        "ASSIGNED": "assigned",
        "IN_PROGRESS": "in_progress",
        "RESOLVED": "resolved",
        "CLOSED": "closed",
        "APPROVED": "approved",
    }
    return mapping.get(arin_status, "pending_review")
```

**Step 3: Add URL patterns for actions**

Add to `netbox_rir_manager/urls.py`:

```python
path("networks/<int:pk>/reassign/", views.RIRNetworkReassignView.as_view(), name="rirnetwork_reassign"),
path("networks/<int:pk>/reallocate/", views.RIRNetworkReallocateView.as_view(), name="rirnetwork_reallocate"),
path("networks/<int:pk>/remove/", views.RIRNetworkRemoveView.as_view(), name="rirnetwork_remove"),
path("networks/<int:pk>/delete-arin/", views.RIRNetworkDeleteARINView.as_view(), name="rirnetwork_delete_arin"),
```

**Step 4: Update RIRNetwork detail template with action buttons**

Update `netbox_rir_manager/templates/netbox_rir_manager/rirnetwork.html` to add an "ARIN Actions" card:

```html
{# Add after the NetBox Links card, inside the left column #}
<div class="card">
    <h5 class="card-header">ARIN Actions</h5>
    <div class="card-body">
        <a href="{% url 'plugins:netbox_rir_manager:rirnetwork_reassign' object.pk %}"
           class="btn btn-sm btn-primary me-1">
            <i class="mdi mdi-swap-horizontal"></i> Reassign
        </a>
        <a href="{% url 'plugins:netbox_rir_manager:rirnetwork_reallocate' object.pk %}"
           class="btn btn-sm btn-info me-1">
            <i class="mdi mdi-arrow-right-bold"></i> Reallocate
        </a>
        <form method="post" action="{% url 'plugins:netbox_rir_manager:rirnetwork_remove' object.pk %}"
              class="d-inline" onsubmit="return confirm('Remove this network from ARIN?');">
            {% csrf_token %}
            <button type="submit" class="btn btn-sm btn-warning me-1">
                <i class="mdi mdi-minus-circle"></i> Remove
            </button>
        </form>
        <form method="post" action="{% url 'plugins:netbox_rir_manager:rirnetwork_delete_arin' object.pk %}"
              class="d-inline" onsubmit="return confirm('Submit delete request to ARIN?');">
            {% csrf_token %}
            <button type="submit" class="btn btn-sm btn-danger">
                <i class="mdi mdi-delete"></i> Delete at ARIN
            </button>
        </form>
    </div>
</div>
```

**Step 5: Create form templates**

Create `netbox_rir_manager/templates/netbox_rir_manager/rirnetwork_reassign.html`:

```html
{% extends 'generic/object.html' %}
{% load helpers %}
{% load form_helpers %}

{% block title %}Reassign Network {{ object.handle }}{% endblock %}

{% block content %}
<div class="row mb-3">
    <div class="col col-md-8">
        <div class="card">
            <h5 class="card-header">Reassign Network {{ object.handle }}</h5>
            <div class="card-body">
                <form method="post">
                    {% csrf_token %}
                    {% render_form form %}
                    <div class="text-end">
                        <a href="{{ object.get_absolute_url }}" class="btn btn-outline-secondary">Cancel</a>
                        <button type="submit" class="btn btn-primary">Submit Reassignment</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock content %}
```

Create similar template for `rirnetwork_reallocate.html`.

**Step 6: Write tests**

Test each action view:
- GET reassign form returns 200
- POST reassign with valid data (mocked backend) creates ticket and log, redirects
- POST reassign with no API key returns error message
- POST reassign with backend failure returns error message
- POST remove with mocked backend success/failure
- POST delete-arin with mocked backend success/failure
- Same patterns for reallocate

**Step 7: Run tests**

Run: `python -m pytest netbox_rir_manager/tests/ -v`
Expected: All tests pass

**Step 8: Commit**

```bash
git add netbox_rir_manager/forms.py netbox_rir_manager/views.py netbox_rir_manager/urls.py \
  netbox_rir_manager/templates/netbox_rir_manager/rirnetwork.html \
  netbox_rir_manager/templates/netbox_rir_manager/rirnetwork_reassign.html \
  netbox_rir_manager/templates/netbox_rir_manager/rirnetwork_reallocate.html \
  netbox_rir_manager/tests/
git commit -m "feat: add network write action views (reassign, reallocate, remove, delete)"
```

---

### Task 5: Add REST API Write Actions and Ticket Refresh

**Files:**
- Modify: `netbox_rir_manager/api/serializers.py`
- Modify: `netbox_rir_manager/api/views.py`
- Modify: `netbox_rir_manager/views.py`
- Modify: `netbox_rir_manager/urls.py`

**Step 1: Add API action serializers**

Add to `netbox_rir_manager/api/serializers.py`:

```python
class NetworkReassignSerializer(serializers.Serializer):
    reassignment_type = serializers.ChoiceField(choices=["simple", "detailed"])
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    street_address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=2, required=False, allow_blank=True)
    org_handle = serializers.CharField(max_length=50, required=False, allow_blank=True)
    net_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    start_address = serializers.IPAddressField()
    end_address = serializers.IPAddressField()

    def validate(self, data):
        rtype = data.get("reassignment_type")
        if rtype == "simple":
            for field in ("customer_name", "city", "country"):
                if not data.get(field):
                    raise serializers.ValidationError({field: f"Required for simple reassignment."})
        elif rtype == "detailed":
            if not data.get("org_handle"):
                raise serializers.ValidationError({"org_handle": "Required for detailed reassignment."})
        return data


class NetworkReallocateSerializer(serializers.Serializer):
    org_handle = serializers.CharField(max_length=50)
    net_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    start_address = serializers.IPAddressField()
    end_address = serializers.IPAddressField()
```

**Step 2: Add custom actions to RIRNetworkViewSet**

Add to `RIRNetworkViewSet` in `netbox_rir_manager/api/views.py`:

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class RIRNetworkViewSet(NetBoxModelViewSet):
    # ... existing ...

    @action(detail=True, methods=["post"], url_path="reassign")
    def reassign(self, request, pk=None):
        """Reassign a subnet from this network via ARIN API."""
        # Validate input, get user_key, call backend, create ticket, return result
        ...

    @action(detail=True, methods=["post"], url_path="reallocate")
    def reallocate(self, request, pk=None):
        """Reallocate a subnet from this network via ARIN API."""
        ...

    @action(detail=True, methods=["post"], url_path="remove")
    def remove_net(self, request, pk=None):
        """Remove a reassigned/reallocated network from ARIN."""
        ...

    @action(detail=True, methods=["post"], url_path="delete-arin")
    def delete_arin(self, request, pk=None):
        """Delete a network at ARIN (creates a ticket)."""
        ...
```

Each action follows the same pattern as the Django views: validate input, get user_key, call backend, create ticket/log, return JSON response.

**Step 3: Add ticket refresh**

Add a `refresh` action to `RIRTicketViewSet`:

```python
class RIRTicketViewSet(NetBoxModelViewSet):
    # ... existing ...

    @action(detail=True, methods=["post"], url_path="refresh")
    def refresh(self, request, pk=None):
        """Refresh ticket status from ARIN."""
        # Fetch ticket status from ARIN, update local record
        ...
```

Add a corresponding Django view `RIRTicketRefreshView` and URL pattern:

```python
path("tickets/<int:pk>/refresh/", views.RIRTicketRefreshView.as_view(), name="rirticket_refresh"),
```

Add a "Refresh Status" button to `rirticket.html`.

**Step 4: Write tests**

Test each API action:
- POST reassign with valid data (mocked backend) returns 200 with ticket info
- POST reassign with invalid data returns 400
- POST reassign with no API key returns 403
- Same patterns for reallocate, remove, delete-arin
- POST refresh updates ticket status

**Step 5: Run tests**

Run: `python -m pytest netbox_rir_manager/tests/ -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add netbox_rir_manager/api/ netbox_rir_manager/views.py netbox_rir_manager/urls.py \
  netbox_rir_manager/templates/netbox_rir_manager/rirticket.html \
  netbox_rir_manager/tests/
git commit -m "feat: add REST API write actions and ticket refresh"
```

---

### Task 6: Add SyncLog Operation Choices for Write Ops and Final Cleanup

**Files:**
- Modify: `netbox_rir_manager/choices.py`
- All files for linting

**Step 1: Add write-specific operation choices**

Add to `SyncOperationChoices` in `choices.py`:

```python
CHOICES = [
    ("sync", "Sync", "blue"),
    ("create", "Create", "green"),
    ("update", "Update", "yellow"),
    ("delete", "Delete", "red"),
    ("reassign", "Reassign", "purple"),
    ("reallocate", "Reallocate", "indigo"),
    ("remove", "Remove", "orange"),
]
```

Update the views to use the correct operation values in `RIRSyncLog.objects.create()` calls.

**Step 2: Run linting**

Run: `ruff check netbox_rir_manager/ --fix && ruff format netbox_rir_manager/`

**Step 3: Run full test suite**

Run: `python -m pytest netbox_rir_manager/tests/ -v --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add write operation choices, final linting pass"
```
