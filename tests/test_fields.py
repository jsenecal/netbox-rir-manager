import pytest


@pytest.mark.django_db
class TestEncryptedCharField:
    def test_encrypts_on_save_and_decrypts_on_read(self, rir_config, admin_user):
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="my-secret-key")
        key.refresh_from_db()
        # Python attribute returns plaintext
        assert key.api_key == "my-secret-key"

    def test_raw_db_value_is_encrypted(self, rir_config, admin_user):
        from django.db import connection

        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="my-secret-key")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT api_key FROM netbox_rir_manager_riruserkey WHERE id = %s",
                [key.pk],
            )
            raw_value = cursor.fetchone()[0]
        assert raw_value.startswith("$FERNET$")
        assert "my-secret-key" not in raw_value

    def test_handles_empty_string(self, rir_config, admin_user):
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="")
        key.refresh_from_db()
        assert key.api_key == ""

    def test_handles_none(self, rir_config, admin_user):
        """None values pass through without encryption."""
        from netbox_rir_manager.fields import EncryptedCharField

        field = EncryptedCharField(max_length=512)
        assert field.get_prep_value(None) is None
        assert field.from_db_value(None, None, None) is None

    def test_idempotent_encryption(self, rir_config, admin_user):
        """Saving twice doesn't double-encrypt."""
        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="idempotent-key")
        key.save()  # second save
        key.refresh_from_db()
        assert key.api_key == "idempotent-key"

    def test_plaintext_migrated_on_read(self, rir_config, admin_user):
        """A plaintext value in the DB (pre-migration) decrypts correctly."""
        from django.db import connection

        from netbox_rir_manager.models import RIRUserKey

        key = RIRUserKey.objects.create(user=admin_user, rir_config=rir_config, api_key="will-be-forced-plain")
        # Simulate a pre-migration plaintext value
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE netbox_rir_manager_riruserkey SET api_key = %s WHERE id = %s",
                ["old-plain-key", key.pk],
            )
        key.refresh_from_db()
        assert key.api_key == "old-plain-key"
