# User API Keys

Each NetBox user attaches their own RIR credential to one or more `RIRConfig` rows. Keys are encrypted at rest and never returned by the REST API after creation.

## Why per-user keys

The plugin assumes a multi-tenant operations model. RIR audit trails attribute every change to the credential that submitted it, so the plugin records, on every synced or written object:

- `synced_by` -- the `RIRUserKey` whose call produced the row (on `RIROrganization`, `RIRContact`, `RIRNetwork`).
- `submitted_by` -- the `RIRUserKey` that submitted a write (on `RIRTicket`).

Per-user keys also avoid the operational hazard of a shared secret, and make rotation a per-user concern.

## Adding a key

1. Go to **RIR Manager > User Keys** and click **Add**.
2. Pick a NetBox user (admins can create keys for other users).
3. Pick the **RIR Config**. The pair (user, config) must be unique.
4. Paste the API key into the password input.
5. Save.

The form widget uses `forms.PasswordInput`, so the value is masked while typing. The serializer marks `api_key` as `write_only`, so it is never echoed back over the REST API.

## Encryption at rest

The `RIRUserKey.api_key` column is an `EncryptedCharField`. Saving it transparently runs the value through Fernet encryption with a key derived from the plugin's `encryption_key` setting (or NetBox's `SECRET_KEY` when the setting is empty). Reading it (via the ORM) transparently decrypts.

Implementation details:

- **KDF**: HKDF-SHA256, salt `netbox-rir-manager`, info `api-key-encryption`, output 32 bytes.
- **Cipher**: Fernet (AES-128-CBC + HMAC-SHA256 + IV).
- **Storage prefix**: `$FERNET$<token>`. Values without the prefix are returned as-is, which preserves backward compatibility with rows written before the field was added.
- **Decryption failure mode**: `InvalidToken` returns the stored value verbatim instead of raising. This means a misconfigured `encryption_key` will not crash the application, but write operations will fail at the RIR with confusing errors. See the warning below.

The implementation is `netbox_rir_manager.fields.EncryptedCharField`.

## Rotation

Rotating a single user's RIR API key:

1. Update the key with the RIR.
2. Edit the `RIRUserKey` row in NetBox and paste the new value.
3. Save. The new ciphertext replaces the old.

Rotating the `encryption_key` setting:

1. Pre-flight: write a one-shot Django shell snippet that loops over every `RIRUserKey`, reads `api_key` (which decrypts under the old key), and `save()`s it back (which re-encrypts under the same old key). This guarantees no plaintext rows remain.
2. Update `encryption_key` in `configuration.py`.
3. Restart NetBox and the RQ worker.
4. Have each user re-enter their key. There is no way to recover the old ciphertext under the new key.

!!! warning "Lost keys are unrecoverable"

    Changing or losing `encryption_key` (or `SECRET_KEY` when the plugin's setting is empty) makes every previously encrypted API key unrecoverable. Treat the encryption key like a database password: store it in your secrets manager and back it up alongside the database.

## REST API

```http
GET  /api/plugins/rir-manager/user-keys/
POST /api/plugins/rir-manager/user-keys/
GET  /api/plugins/rir-manager/user-keys/{id}/
PATCH /api/plugins/rir-manager/user-keys/{id}/
DELETE /api/plugins/rir-manager/user-keys/{id}/
```

`api_key` is `write_only`. List and retrieve responses omit it entirely.

Example create:

```bash
curl -X POST https://netbox.example.com/api/plugins/rir-manager/user-keys/ \
    -H "Authorization: Token <netbox-token>" \
    -H "Content-Type: application/json" \
    -d '{
      "user": 1,
      "rir_config": 1,
      "api_key": "API-XXXX-XXXX-XXXX-XXXX"
    }'
```

## Filtering

The list view filters by `user` and `rir_config_id`. Search matches `user.username`.

## Permissions

To use sync and write actions, a user needs:

- `netbox_rir_manager.view_rirconfig` on the target config.
- `netbox_rir_manager.view_riruserkey` and `netbox_rir_manager.add_riruserkey` to manage their own key.
- The relevant `change_*` permission on the resource being modified.

Admins managing keys for other users additionally need `netbox_rir_manager.add_riruserkey` and `change_riruserkey`. See [Reference: Permissions](../reference/permissions.md).
