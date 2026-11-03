# Backends

A backend is the code that talks to one RIR's API. The plugin ships one: ARIN, through [`pyregrws`](https://pypi.org/project/pyregrws/).

## Current state

The plugin is laid out for several backends, but only ARIN is wired in:

- `netbox_rir_manager/backends/base.py` defines the abstract `RIRBackend` interface.
- `netbox_rir_manager/backends/__init__.py` keeps a registry: the `@register_backend` decorator adds a class to `BACKENDS` under its `name`, and `get_backend(name)` looks one up.
- The views, REST API actions and jobs construct `ARINBackend` directly. Nothing looks a backend up from the registry or from the RIR of a config, and the `enabled_backends` setting is not read.

Adding another RIR therefore takes more than a new `RIRBackend` subclass: the call sites must also choose the backend for each config. The sync also relies on `find_net`, which `ARINBackend` provides but `RIRBackend` does not declare.

## The RIRBackend interface

| Method | Returns |
|--------|---------|
| `authenticate(rir_config)` | Whether the credentials work. |
| `get_organization(handle)` | The organization as a dict, or `None`. |
| `get_poc(handle)` | The point of contact as a dict, or `None`. |
| `get_network(handle)` | The network as a dict, or `None`. |
| `get_customer(handle)` | The customer as a dict, or `None`. |
| `get_asn(asn)` | The ASN as a dict, or `None`. |
| `sync_resources(rir_config, resource_type=None)` | A list of synced resource dicts. |
| `update_network(handle, data)` | The updated network dict, or `None`. |
| `reassign_network(parent_handle, net_data)` | Ticket details, or `None`. |
| `reallocate_network(parent_handle, net_data)` | Ticket details, or `None`. |
| `remove_network(handle)` | `True` on success. |
| `delete_network(handle)` | Ticket details, or `None`. |
| `create_customer(parent_net_handle, data)` | The customer as a dict, or `None`. |

For the write methods, `None` (or `False` from `remove_network`) means the RIR could not be reached. Two exceptions from `backends/base.py` report the other failures, and their messages are shown to the user:

- `RIRDataError`: the data cannot form a valid request, so nothing was sent. The REST API answers `400`.
- `RIRRequestError`: the RIR refused the request; the message is the RIR's reason. The REST API answers `502`.

## The ARIN backend

`ARINBackend` (`netbox_rir_manager/backends/arin.py`) registers itself under the name `ARIN`.

- **Connection**: `ARINBackend.for_user_key(user_key)` builds a `pyregrws` client with the key's API key and, when set, the key's config's **API URL** in place of the `pyregrws` default.
- **Retries**: every call is retried on `ConnectionError`, `OSError` and `TimeoutError`, as set by `api_retry_count` and `api_retry_backoff` (see [Settings](settings.md)). An error response from ARIN is not retried.
- **Reads** return `None` when the call fails or ARIN answers with an error.
- **Writes** raise `RIRRequestError` with ARIN's reason when ARIN answers with an error, and raise `RIRDataError` when `pyregrws` rejects the payload or the customer's country is not an ISO 3166-1 alpha-2 code. Customer details are converted to ASCII before they are sent.
- **Not implemented**: `get_asn` always returns `None` and `sync_resources` always returns an empty list. The sync does not use them; it calls `get_organization`, `get_poc`, `find_net` and `get_network` itself (see [Syncing Resources](../user-guide/syncing.md)).
