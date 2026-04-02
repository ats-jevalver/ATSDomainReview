"""WHOIS data collector using python-whois."""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import whois

from models import WhoisData

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=10)


def _normalize_date(value: Any) -> datetime | None:
    """Convert a WHOIS date value to a single datetime object."""
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


def _normalize_name_servers(ns: Any) -> list[str]:
    """Normalize name server values into a list of strings."""
    if ns is None:
        return []
    if isinstance(ns, str):
        return [ns.lower()]
    if isinstance(ns, list):
        return [s.lower() for s in ns if isinstance(s, str)]
    return []


def _sync_whois_lookup(domain: str) -> WhoisData:
    """Perform a synchronous WHOIS lookup (runs in thread pool)."""
    try:
        w = whois.whois(domain)
    except Exception as exc:
        logger.warning("WHOIS lookup failed for %s: %s", domain, exc)
        return WhoisData(privacy_protected=True)

    if w is None or w.domain_name is None:
        return WhoisData(privacy_protected=True)

    registrar = w.registrar if hasattr(w, "registrar") else None
    registrant = None
    privacy_protected = False

    # Detect privacy protection
    org = getattr(w, "org", None) or ""
    if isinstance(org, str) and any(
        kw in org.lower()
        for kw in ["privacy", "proxy", "redacted", "whoisguard", "domains by proxy", "contact privacy"]
    ):
        privacy_protected = True
    elif registrant is None and getattr(w, "name", None) is None:
        privacy_protected = True

    registrant_name = getattr(w, "name", None)
    if isinstance(registrant_name, list):
        registrant_name = registrant_name[0] if registrant_name else None
    if registrant_name and isinstance(registrant_name, str):
        if any(kw in registrant_name.lower() for kw in ["redacted", "privacy", "not disclosed"]):
            privacy_protected = True
            registrant_name = None
    registrant = registrant_name

    return WhoisData(
        registrar=registrar,
        creation_date=_normalize_date(getattr(w, "creation_date", None)),
        expiration_date=_normalize_date(getattr(w, "expiration_date", None)),
        updated_date=_normalize_date(getattr(w, "updated_date", None)),
        name_servers=_normalize_name_servers(getattr(w, "name_servers", None)),
        registrant=registrant,
        privacy_protected=privacy_protected,
    )


def _sync_whois_with_retry(domain: str, retries: int = 3, backoff: float = 2.0) -> WhoisData:
    """WHOIS lookup with retries and exponential back-off.

    WHOIS servers are rate-limited and flaky — a single attempt often
    returns partial data or times out. Retrying with a short delay
    dramatically improves consistency.
    """
    last_result = WhoisData(privacy_protected=True)
    for attempt in range(retries):
        result = _sync_whois_lookup(domain)
        # If we got a registrar back, the lookup was successful
        if result.registrar:
            return result
        last_result = result
        if attempt < retries - 1:
            delay = backoff * (attempt + 1)
            logger.info("WHOIS retry %d/%d for %s in %.1fs", attempt + 2, retries, domain, delay)
            time.sleep(delay)
    return last_result


async def collect_whois(domain: str, timeout: int = 30) -> WhoisData:
    """Collect WHOIS data for a domain.

    Runs the synchronous python-whois library in a thread executor
    with retries and a generous timeout (WHOIS servers are slow).
    """
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _sync_whois_with_retry, domain),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("WHOIS lookup timed out for %s", domain)
        return WhoisData(privacy_protected=True)
    except Exception as exc:
        logger.error("WHOIS collection error for %s: %s", domain, exc)
        return WhoisData(privacy_protected=True)
