# RIR backend choices for model fields
RIR_BACKEND_CHOICES = [
    ("ARIN", "ARIN"),
    ("RIPE", "RIPE NCC"),
    ("APNIC", "APNIC"),
    ("LACNIC", "LACNIC"),
    ("AFRINIC", "AFRINIC"),
]

# Shown wherever an action needs the requesting user's own key on a config and they have none
NO_API_KEY_MESSAGE = "No API key configured for this RIR config."
