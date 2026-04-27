# User API Keys

Each NetBox user attaches their own API key to an RIR Config. Keys are encrypted at rest using the configured `encryption_key` (or NetBox's `SECRET_KEY` when empty).

## Adding a key

1. Navigate to **RIR Manager → User Keys** and click **Add**.
2. Select the RIR Config.
3. Paste your RIR API key (e.g. ARIN Online API key).
4. Save.

The key is encrypted before persistence and is never displayed in cleartext after creation.

!!! warning "Key rotation"

    Changing the `encryption_key` setting (or NetBox's `SECRET_KEY` when the plugin's setting is empty) makes all previously encrypted API keys unrecoverable.
