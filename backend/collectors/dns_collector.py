"""DNS record collector using dnspython."""

from __future__ import annotations

import asyncio
import logging

import dns.asyncresolver
import dns.exception
import dns.name
import dns.rdatatype
import dns.resolver

from models import DnsData, DnssecData

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0


async def _resolve(domain: str, rdtype: str) -> list[str]:
    """Resolve a single DNS record type, returning a list of string values."""
    try:
        resolver = dns.asyncresolver.Resolver()
        resolver.lifetime = _TIMEOUT
        resolver.timeout = _TIMEOUT
        answers = await resolver.resolve(domain, rdtype)
        results = []
        for rdata in answers:
            text = rdata.to_text().strip('"')
            results.append(text)
        return results
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
        dns.name.EmptyLabel,
    ):
        return []
    except Exception as exc:
        logger.warning("DNS resolve failed for %s %s: %s", domain, rdtype, exc)
        return []


async def collect_dns(domain: str) -> DnsData:
    """Collect all common DNS records for a domain."""
    a, aaaa, cname, mx, ns, txt = await asyncio.gather(
        _resolve(domain, "A"),
        _resolve(domain, "AAAA"),
        _resolve(domain, "CNAME"),
        _resolve(domain, "MX"),
        _resolve(domain, "NS"),
        _resolve(domain, "TXT"),
    )

    return DnsData(
        a_records=a,
        aaaa_records=aaaa,
        cname_records=cname,
        mx_records=mx,
        ns_records=ns,
        txt_records=txt,
    )


async def collect_dnssec(domain: str) -> DnssecData:
    """Check if DNSSEC is enabled for a domain."""
    try:
        resolver = dns.asyncresolver.Resolver()
        resolver.lifetime = _TIMEOUT
        resolver.timeout = _TIMEOUT
        answers = await resolver.resolve(domain, "DNSKEY")
        if answers:
            return DnssecData(
                enabled=True,
                details=f"DNSSEC is enabled with {len(answers)} DNSKEY record(s).",
            )
    except dns.resolver.NoAnswer:
        return DnssecData(enabled=False, details="No DNSKEY records found; DNSSEC is not enabled.")
    except dns.resolver.NXDOMAIN:
        return DnssecData(enabled=False, details="Domain does not exist in DNS.")
    except dns.exception.Timeout:
        return DnssecData(enabled=False, details="DNSSEC check timed out.")
    except Exception as exc:
        logger.warning("DNSSEC check failed for %s: %s", domain, exc)
        return DnssecData(enabled=False, details=f"DNSSEC check failed: {exc}")

    return DnssecData(enabled=False, details="No DNSKEY records found; DNSSEC is not enabled.")
