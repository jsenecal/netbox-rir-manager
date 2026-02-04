from utilities.choices import ChoiceSet


class SyncOperationChoices(ChoiceSet):
    key = "RIRSyncLog.operation"

    CHOICES = [
        ("sync", "Sync", "blue"),
        ("create", "Create", "green"),
        ("update", "Update", "yellow"),
        ("delete", "Delete", "red"),
    ]


class SyncStatusChoices(ChoiceSet):
    key = "RIRSyncLog.status"

    CHOICES = [
        ("success", "Success", "green"),
        ("error", "Error", "red"),
        ("skipped", "Skipped", "gray"),
    ]


class ContactTypeChoices(ChoiceSet):
    key = "RIRContact.contact_type"

    CHOICES = [
        ("PERSON", "Person", "blue"),
        ("ROLE", "Role", "purple"),
    ]
