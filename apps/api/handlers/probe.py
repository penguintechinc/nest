"""TCP probe utilities for introspection."""

import asyncio
import ipaddress
import re
import socket
from typing import Optional, Tuple


class BlockedTargetError(Exception):
    """Raised when a probe target resolves to a non-public / internal address.

    Used as an SSRF / internal port-scan guard so the introspect path cannot be
    pointed at loopback, cloud metadata, or private cluster addresses.
    """


def _blocked_ip_reason(ip: str) -> Optional[str]:
    """Return a reason string if ``ip`` must not be probed, else None.

    Rejects loopback (127.0.0.0/8, ::1), link-local incl. the cloud metadata
    endpoint (169.254.0.0/16 → 169.254.169.254, fe80::/10), RFC1918 private
    ranges (10/8, 172.16/12, 192.168/16), unique-local IPv6 (fc00::/7 incl.
    fd00:ec2::254), CGNAT, multicast, reserved, unspecified, and any other
    address that is not globally routable.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return "unparseable address"

    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:10.0.0.1) so IPv4 rules apply.
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        addr = mapped

    if addr.is_loopback:
        return "loopback address"
    if addr.is_link_local:
        return "link-local address"
    if addr.is_private:
        return "private address"
    if addr.is_multicast:
        return "multicast address"
    if addr.is_reserved:
        return "reserved address"
    if addr.is_unspecified:
        return "unspecified address"
    if not addr.is_global:
        return "non-global address"
    return None


async def resolve_public_target(
    host: str, port: int, timeout: float = 5.0
) -> Optional[str]:
    """Resolve ``host`` and return a validated, globally-routable IP string.

    Returns the validated IP to connect to, or None if the host could not be
    resolved (treated as "not reachable", not a security rejection).

    Raises BlockedTargetError if the host resolves to any non-public address.
    Callers must connect to the returned IP directly (not re-resolve the
    hostname) so a DNS-rebind cannot swap in an internal address afterwards.
    """
    if not host:
        return None

    loop = asyncio.get_event_loop()
    try:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, OSError):
        return None

    if not infos:
        return None

    # Reject if ANY resolved address is non-public (defends against a record
    # set that mixes a public decoy with an internal target).
    for info in infos:
        ip = info[4][0]
        reason = _blocked_ip_reason(ip)
        if reason:
            raise BlockedTargetError(
                f"refusing to probe non-public address {ip}: {reason}"
            )

    # All resolved addresses passed validation; return the first one.
    return infos[0][4][0]


def extract_host_port(
    conn_str: str, default_port: int = 5432
) -> Optional[Tuple[str, int]]:
    """Extract host:port from a connection string.

    Handles formats like:
    - postgresql://host:5432/db
    - host:5432
    - host (uses default_port)
    """
    if not conn_str:
        return None

    # Try postgres:// URI format
    if "://" in conn_str:
        match = re.search(r"://([^/:]+):?(\d+)?", conn_str)
        if match:
            host = match.group(1)
            port = int(match.group(2)) if match.group(2) else default_port
            return (host, port)

    # Try host:port format
    if ":" in conn_str:
        parts = conn_str.rsplit(":", 1)
        try:
            port = int(parts[1])
            return (parts[0], port)
        except ValueError:
            pass

    # Just host, use default port
    return (conn_str, default_port)


async def tcp_ping(host: str, port: int, timeout: float = 5.0) -> Tuple[bool, int, str]:
    """Probe TCP connection to host:port.

    Returns: (reachable, latency_ms, message)
    """
    import time

    start = time.time()
    try:
        await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        latency_ms = int((time.time() - start) * 1000)
        return True, latency_ms, "tcp connection successful"
    except asyncio.TimeoutError:
        return False, int(timeout * 1000), f"connection timeout after {timeout}s"
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return False, latency_ms, str(e)
