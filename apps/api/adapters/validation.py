"""Input validators (adapter for the unpublished ``penguin-validation`` package)."""

import re

_RESOURCE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_DNS_LABEL_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_DNS_LABEL_MAX = 63


def validate_resource_id(value: str) -> str:
    """Return ``value`` if it is a safe resource id, else raise ``ValueError``.

    Mirrors the gateway ``validResourceID`` SSRF guard: only letters, digits,
    underscore and hyphen, so an id can never smuggle path or query syntax.
    """
    # fullmatch, not match/$: "$" would accept a trailing newline ("a\n").
    if not isinstance(value, str) or _RESOURCE_ID_RE.fullmatch(value) is None:
        raise ValueError("invalid resource id")
    return value


def validate_dns_label(value: str) -> str:
    """Return ``value`` if it is a valid RFC 1123 DNS label, else raise ``ValueError``.

    Lowercase alphanumerics and hyphens, starting and ending alphanumeric, at most
    63 characters; used for names that become Kubernetes object or host names.
    """
    if (
        not isinstance(value, str)
        or len(value) > _DNS_LABEL_MAX
        or _DNS_LABEL_RE.fullmatch(value) is None
    ):
        raise ValueError("invalid DNS-1123 label")
    return value
