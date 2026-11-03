"""ARIN network name rules.

ARIN's reassignment templates allow "up to 50 letters and/or numbers" plus dashes, and Reg-RWS
rejects any NET name with characters "that are not letters, numbers, hyphens, or spaces".
Payloads are ASCII-only, so accented letters are not accepted either.
"""

import re
import unicodedata

from django.core.exceptions import ValidationError

ARIN_NET_NAME_MAX_LENGTH = 50

_NET_NAME_RE = re.compile(r"^[A-Za-z0-9 -]+$")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")


def to_ascii(text) -> str:
    """Transliterate accented letters to their ASCII base letter and drop any other non-ASCII character."""
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()


def _slug(text) -> str:
    """Uppercase ASCII with every run of other characters collapsed to a single hyphen."""
    return _NON_ALNUM_RE.sub("-", to_ascii(text).upper()).strip("-")


def build_net_name(label, prefix) -> str:
    """Build an ARIN-valid net name from a label (e.g. a tenant name) and a prefix.

    The prefix is what makes the name unique, so when the result would exceed ARIN's limit
    the label is shortened and the prefix kept whole.
    """
    suffix = _slug(prefix)
    budget = ARIN_NET_NAME_MAX_LENGTH - len(suffix) - 1
    label_part = _slug(label)[: max(budget, 0)].rstrip("-")
    return f"{label_part}-{suffix}" if label_part else suffix


def validate_net_name(value):
    """Reject characters ARIN refuses in a net name; the form and API fields enforce the length."""
    if not _NET_NAME_RE.match(value):
        raise ValidationError("ARIN net names may contain only ASCII letters, numbers, hyphens and spaces.")
