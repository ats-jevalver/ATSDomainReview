"""DKIM record collector."""

from __future__ import annotations

import asyncio
import logging

import dns.asyncresolver
import dns.exception
import dns.resolver

from models import DkimData

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0

# Comprehensive list of common DKIM selectors used by major providers.
COMMON_SELECTORS = [
    # Microsoft 365 / Exchange Online
    "selector1",
    "selector2",
    # Google Workspace
    "google",
    "default",
    # SendGrid
    "s1",
    "s2",
    "smtpapi",
    # Mailchimp / Mandrill
    "k1",
    "k2",
    "k3",
    "mandrill",
    # Amazon SES
    "ses",
    "amazonses",
    # Mailgun
    "smtp",
    "mailo",
    "mg",
    # Proton Mail
    "protonmail",
    "protonmail2",
    "protonmail3",
    # Zoho
    "zoho",
    "zmail",
    # Fastmail
    "fm1",
    "fm2",
    "fm3",
    # Postmark
    "pm",
    # Brevo (Sendinblue)
    "mail",
    # Mimecast
    "mimecast20190104",
    "mimecast",
    # Generic / common
    "dkim",
    "key1",
    "key2",
    "email",
    "mta",
    "e",
    "cm",
    # Constant Contact
    "ctct1",
    "ctct2",
    # Hubspot
    "hs1",
    "hs2",
    "hubspot",
    # Klaviyo
    "kl",
    "kl2",
    # Salesforce
    "sf",
    "sf1",
    "salesforce",
    "sf2",
]


async def _check_selector(domain: str, selector: str) -> tuple[str, str | None]:
    """Check a single DKIM selector, returning (selector, record_or_none)."""
    qname = f"{selector}._domainkey.{domain}"
    try:
        resolver = dns.asyncresolver.Resolver()
        resolver.lifetime = _TIMEOUT
        resolver.timeout = _TIMEOUT
        answers = await resolver.resolve(qname, "TXT")
        for rdata in answers:
            # Concatenate split TXT strings and strip outer quotes
            parts = []
            for s in rdata.strings:
                if isinstance(s, bytes):
                    parts.append(s.decode("utf-8", errors="replace"))
                else:
                    parts.append(str(s))
            txt = "".join(parts)
            if txt:
                return (selector, txt)
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ):
        pass
    except Exception as exc:
        logger.debug("DKIM check for %s failed: %s", qname, exc)
    return (selector, None)


async def collect_dkim(domain: str) -> DkimData:
    """Check common DKIM selectors for a domain.

    Queries ``{selector}._domainkey.{domain}`` TXT records for each
    common selector name. Uses a broad list covering Microsoft 365,
    Google, SendGrid, Mailchimp, Amazon SES, and many more.
    """
    tasks = [_check_selector(domain, sel) for sel in COMMON_SELECTORS]
    results = await asyncio.gather(*tasks)

    selectors_found: list[str] = []
    records: dict[str, str] = {}

    for selector, record in results:
        if record is not None:
            selectors_found.append(selector)
            records[selector] = record

    return DkimData(
        found=len(selectors_found) > 0,
        selectors_checked=list(COMMON_SELECTORS),
        selectors_found=selectors_found,
        records=records,
    )
