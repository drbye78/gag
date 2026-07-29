"""
Security utilities for URL validation, SSRF prevention, and filename sanitization.

Provides:
- validate_url: SSRF-safe URL validation with private IP blocking
- sanitize_filename: Path traversal prevention for filenames
"""

import ipaddress
import re
from urllib.parse import urlparse


# Private/loopback/link-local networks to block for SSRF prevention
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

# Cloud metadata endpoint
_METADATA_IP = ipaddress.ip_address("169.254.169.254")


def validate_url(url: str, allowed_domain: str | None = None) -> str:
    """Validate a URL for safe HTTP/HTTPS usage, blocking SSRF targets.

    Parses the URL and rejects:
    - Non-HTTP/HTTPS schemes
    - Private/internal IP addresses (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x, ::1, fc00::/7)
    - Cloud metadata endpoints (169.254.169.254)
    - Hostnames that don't match an optional allowed_domain

    Args:
        url: The URL to validate.
        allowed_domain: If provided, the URL hostname must match this domain.

    Returns:
        The validated URL string.

    Raises:
        ValueError: If the URL is invalid, uses a blocked scheme/IP, or fails domain check.
    """
    parsed = urlparse(url)

    # Scheme check
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme '{parsed.scheme}': only http and https are allowed"
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have a valid hostname")

    # Check against allowed domain
    if allowed_domain is not None:
        # Allow exact match or subdomain match
        if hostname != allowed_domain and not hostname.endswith(f".{allowed_domain}"):
            raise ValueError(
                f"URL hostname '{hostname}' does not match allowed domain '{allowed_domain}'"
            )

    # Check if hostname is an IP address (resolve for SSRF check)
    try:
        ip = ipaddress.ip_address(hostname)
        # Block private/loopback/link-local IPs
        if ip == _METADATA_IP:
            raise ValueError("Access to cloud metadata endpoint 169.254.169.254 is blocked")
        for network in _PRIVATE_NETWORKS:
            if ip in network:
                raise ValueError(
                    f"URL resolves to private/internal IP '{ip}' which is blocked for SSRF prevention"
                )
    except ValueError as e:
        # If it's our ValueError, re-raise it
        if "blocked" in str(e) or "metadata" in str(e):
            raise
        # If ip_address() failed, hostname is a DNS name, not a literal IP.
        # We cannot block DNS rebinding at parse time, but we block literal IPs.
        pass

    return url


def sanitize_filename(name: str) -> str:
    """Sanitize a filename to prevent path traversal attacks.

    Strips path separators, null bytes, and leading dots that could
    be used for directory traversal.

    Args:
        name: The raw filename to sanitize.

    Returns:
        A sanitized filename string.

    Raises:
        ValueError: If the filename is empty after sanitization.
    """
    if not name:
        raise ValueError("Filename cannot be empty")

    # Remove null bytes
    sanitized = name.replace("\x00", "")

    # Remove path separators (both Unix and Windows)
    sanitized = sanitized.replace("/", "").replace("\\", "")

    # Remove leading dots (prevent hidden files and relative path tricks)
    sanitized = sanitized.lstrip(".")

    if not sanitized:
        raise ValueError("Filename is empty after sanitization")

    return sanitized


def safe_cypher_identifier(name: str, max_length: int = 64) -> str:
    """Sanitize a string for use as a Cypher node/relationship label or identifier.

    Allows only alphanumeric characters and underscores.
    Replaces all other characters with underscores.
    Truncates to max_length if too long.

    Args:
        name: Raw identifier string
        max_length: Maximum allowed length (default 64)

    Returns:
        Safe identifier string for Cypher queries
    """
    # Replace any non-alphanumeric, non-underscore char with underscore
    safe = re.sub(r'[^A-Za-z0-9_]', '_', name)
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Strip leading/trailing underscores
    safe = safe.strip('_')
    # Truncate
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')
    # Fallback for empty results
    if not safe:
        safe = "node"
    return safe
