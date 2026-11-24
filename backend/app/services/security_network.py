"""
Authoritative SSRF Protection and Safe HTTP Network Client for JARVIS.

Provides fail-closed protection against:
1. Private, loopback, link-local, multicast, and reserved IP ranges (IPv4 and IPv6).
2. Cloud provider metadata services (AWS/GCP/Azure/Oracle/OpenStack).
3. DNS rebinding and dual-homed DNS by verifying all resolved A and AAAA records.
4. HTTP redirect-based SSRF by manually validating every redirect hop destination.
5. Resource exhaustion via strict response-size limits and connection/read timeouts.
"""

import ipaddress
import logging
import socket
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger("jarvis.security_network")

MAX_SAFE_REDIRECTS = 3
MAX_SAFE_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_CONNECT_TIMEOUT = 3.5  # seconds
DEFAULT_READ_TIMEOUT = 7.5  # seconds

# Specific cloud metadata and link-local ranges
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "metadata",
    "169.254.169.254",
    "::1",
    "0.0.0.0",
}

BLOCKED_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),  # Private RFC1918
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),  # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),  # Private RFC1918
    ipaddress.ip_network("198.18.0.0/15"),  # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("::/128"),  # Unspecified
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),  # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),  # Discard prefix
    ipaddress.ip_network("2001:db8::/32"),  # Documentation
    ipaddress.ip_network("fc00::/7"),  # Unique local address (ULA)
    ipaddress.ip_network("fe80::/10"),  # Link-local
    ipaddress.ip_network("ff00::/8"),  # Multicast
]


class SSRFSecurityError(Exception):
    """Raised when an outbound network request targets a forbidden or private address."""
    pass


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address falls into any private, loopback, or reserved range."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True

    for net in BLOCKED_NETWORKS:
        if ip in net:
            return True

    return False


def validate_hostname_ip_resolution(hostname: str) -> list[str]:
    """
    Resolve hostname to IP addresses and ensure ALL resolved records are strictly public.
    Guards against DNS rebinding and dual-homed split-horizon DNS attacks.
    """
    clean_host = hostname.strip().lower().strip("[]")
    if clean_host in BLOCKED_HOSTNAMES:
        raise SSRFSecurityError(f"Access to blocked host '{clean_host}' is prohibited.")

    # If already an IP string
    try:
        ip = ipaddress.ip_address(clean_host)
        if is_ip_blocked(ip):
            raise SSRFSecurityError(f"Access to restricted IP address '{clean_host}' is prohibited.")
        return [str(ip)]
    except ValueError:
        pass

    try:
        addr_infos = socket.getaddrinfo(clean_host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SSRFSecurityError(f"Failed to resolve hostname '{clean_host}': {exc}") from exc

    resolved_ips: list[str] = []
    for info in addr_infos:
        sockaddr = info[4]
        raw_ip = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(raw_ip)
        except ValueError:
            raise SSRFSecurityError(f"Invalid resolved IP '{raw_ip}' for host '{clean_host}'.")

        if is_ip_blocked(ip_obj):
            raise SSRFSecurityError(
                f"Hostname '{clean_host}' resolves to restricted IP address '{raw_ip}' (SSRF blocked)."
            )
        resolved_ips.append(raw_ip)

    if not resolved_ips:
        raise SSRFSecurityError(f"No IP addresses resolved for hostname '{clean_host}'.")

    return resolved_ips


def is_safe_external_url(url: str) -> bool:
    """Quick boolean verification for external URLs."""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False
        validate_hostname_ip_resolution(parsed.hostname)
        return True
    except Exception:
        return False


def safe_http_fetch(
    url: str,
    headers: Optional[dict[str, str]] = None,
    max_bytes: int = MAX_SAFE_RESPONSE_BYTES,
    max_redirects: int = MAX_SAFE_REDIRECTS,
    timeout: tuple[float, float] = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT),
) -> tuple[int, str, dict[str, str]]:
    """
    Safely fetch external web content while strictly validating every redirect hop.
    Returns: (status_code, text_content, response_headers)
    """
    current_url = url.strip()
    redirects_followed = 0

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if headers:
        req_headers.update(headers)

    while True:
        parsed = urlparse(current_url)
        if parsed.scheme not in ("http", "https"):
            raise SSRFSecurityError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are permitted.")
        if not parsed.hostname:
            raise SSRFSecurityError("URL missing valid hostname.")

        # Validate DNS resolution for current hop
        validate_hostname_ip_resolution(parsed.hostname)

        # Do NOT allow automatic redirects — inspect each location manually
        response = requests.get(
            current_url,
            headers=req_headers,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )

        # Handle redirects manually
        if response.status_code in (301, 302, 303, 307, 308):
            redirects_followed += 1
            if redirects_followed > max_redirects:
                raise SSRFSecurityError(f"Exceeded maximum allowed redirect hops ({max_redirects}).")

            location = response.headers.get("Location")
            if not location:
                raise SSRFSecurityError(f"Redirect status code {response.status_code} received without Location header.")

            # Resolve relative redirects
            next_url = urljoin(current_url, location)
            logger.info("SSRF Validator: Inspecting redirect hop %d to %s", redirects_followed, next_url)
            current_url = next_url
            continue

        # Non-redirect response: Read content up to max_bytes
        content_chunks = []
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=16384):
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                logger.warning("Response from %s exceeded size limit (%d bytes); truncating stream.", current_url, max_bytes)
                break
            content_chunks.append(chunk)

        encoding = response.encoding or "utf-8"
        try:
            full_bytes = b"".join(content_chunks)
            text_body = full_bytes.decode(encoding, errors="replace")
        except Exception:
            text_body = ""

        return response.status_code, text_body, dict(response.headers)
