# REST API

Every model and action is exposed via NetBox's REST API under `/api/plugins/rir-manager/`.

## Endpoints

| Endpoint                                       | Resource                          |
|------------------------------------------------|-----------------------------------|
| `/api/plugins/rir-manager/configs/`            | RIR configurations                |
| `/api/plugins/rir-manager/user-keys/`          | Per-user API keys                 |
| `/api/plugins/rir-manager/organizations/`      | RIR organizations                 |
| `/api/plugins/rir-manager/contacts/`           | RIR contacts (POCs)               |
| `/api/plugins/rir-manager/networks/`           | RIR networks                      |
| `/api/plugins/rir-manager/sync-logs/`          | Sync operation logs               |
| `/api/plugins/rir-manager/tickets/`            | RIR tickets                       |

## Authentication

Use NetBox token auth -- see the [NetBox REST API docs](https://netboxlabs.com/docs/netbox/en/stable/integrations/rest-api/).
