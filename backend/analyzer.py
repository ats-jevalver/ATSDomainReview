"""Orchestrates all collectors for domain analysis."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from collectors.whois_collector import collect_whois
from collectors.dns_collector import collect_dns, collect_dnssec
from collectors.ssl_collector import collect_ssl
from collectors.http_collector import collect_http
from collectors.dkim_collector import collect_dkim
from collectors.email_collector import collect_spf, collect_dmarc
from database import create_scan, insert_domain_result, update_scan_status
from models import (
    DkimData,
    DmarcData,
    DnsData,
    DnssecData,
    DomainReport,
    EmailSecurityData,
    HttpData,
    SpfData,
    SslData,
    WhoisData,
)
from models import is_free_email_domain
from scoring import calculate_score

logger = logging.getLogger(__name__)


async def _safe(coro, default):
    """Run a coroutine, returning *default* if it raises."""
    try:
        return await coro
    except Exception as exc:
        logger.error("Collector failed: %s", exc)
        return default


async def analyse_domain(domain: str, scan_id: str, source_emails: list[str] | None = None) -> DomainReport:
    """Run all collectors concurrently for a single domain and score the results.

    Each collector is wrapped so that a failure in one does not prevent the
    others from completing.

    Args:
        domain: The domain name to analyse.
        scan_id: The parent scan identifier.

    Returns:
        A fully populated DomainReport.
    """
    (
        whois_data,
        dns_data,
        dnssec_data,
        ssl_data,
        http_data,
        spf_data,
        dmarc_data,
        dkim_data,
    ) = await asyncio.gather(
        _safe(collect_whois(domain), WhoisData()),
        _safe(collect_dns(domain), DnsData()),
        _safe(collect_dnssec(domain), DnssecData()),
        _safe(collect_ssl(domain), SslData()),
        _safe(collect_http(domain), HttpData()),
        _safe(collect_spf(domain), SpfData()),
        _safe(collect_dmarc(domain), DmarcData()),
        _safe(collect_dkim(domain), DkimData()),
    )

    # Build email security composite
    email_issues: list[str] = list(spf_data.issues) + list(dmarc_data.issues)
    email_recs: list[str] = []
    if not spf_data.record:
        email_recs.append("Publish an SPF record to authorise your mail servers.")
    if not dmarc_data.record:
        email_recs.append("Add a DMARC record to control handling of unauthenticated email.")
    if not dkim_data.found:
        email_recs.append("Configure DKIM to sign outgoing emails for integrity verification.")

    # Simple email sub-score (out of 30 matching the scoring engine)
    email_sub = 0
    if dns_data.mx_records:
        email_sub += 5
    if spf_data.record:
        email_sub += 5
    if spf_data.valid:
        email_sub += 5
    if dmarc_data.record:
        email_sub += 5
    if dmarc_data.policy in ("reject", "quarantine"):
        email_sub += 5
    elif dmarc_data.policy == "none":
        email_sub += 2
    if dkim_data.found:
        email_sub += 5

    email_security = EmailSecurityData(
        spf=spf_data,
        dmarc=dmarc_data,
        dkim=dkim_data,
        mx_records=dns_data.mx_records,
        overall_email_score=email_sub,
        issues=email_issues,
        recommendations=email_recs,
    )

    # Score
    assessment = calculate_score(
        whois=whois_data,
        dns=dns_data,
        spf=spf_data,
        dmarc=dmarc_data,
        dkim=dkim_data,
        dnssec=dnssec_data,
        ssl=ssl_data,
        http=http_data,
    )

    report = DomainReport(
        domain=domain,
        scan_id=scan_id,
        timestamp=datetime.now(timezone.utc),
        is_free_domain=is_free_email_domain(domain),
        source_emails=source_emails or [],
        whois=whois_data,
        dns=dns_data,
        email_security=email_security,
        dnssec=dnssec_data,
        ssl=ssl_data,
        http=http_data,
        security_assessment=assessment,
    )

    return report


async def run_scan(scan_id: str, domains: list[str], email_map: dict[str, list[str]] | None = None) -> None:
    """Run a full scan across multiple domains.

    Processes domains concurrently using a semaphore (max 5 at a time)
    and stores each result in the database.  Updates the scan status on
    completion or failure.

    Args:
        scan_id: The scan identifier.
        domains: List of domain names to scan.
    """
    await update_scan_status(scan_id, "running")
    semaphore = asyncio.Semaphore(5)

    async def _process(domain: str) -> None:
        result_id = str(uuid.uuid4())
        # Insert a placeholder so progress tracking counts this domain.
        # Use COALESCE in the upsert so this null raw_data never overwrites
        # a completed result if there's a race.
        await insert_domain_result(result_id, scan_id, domain, "pending")
        async with semaphore:
            try:
                source_emails = (email_map or {}).get(domain)
                report = await analyse_domain(domain, scan_id, source_emails=source_emails)
                raw = json.loads(report.model_dump_json())
                await insert_domain_result(
                    result_id,
                    scan_id,
                    domain,
                    "completed",
                    raw_data=raw,
                    score=report.security_assessment.overall_score,
                    risk_level=report.security_assessment.risk_level,
                )
            except Exception as exc:
                logger.error("Scan failed for domain %s: %s", domain, exc)
                await insert_domain_result(
                    result_id, scan_id, domain, "failed",
                    raw_data={"error": str(exc)},
                )

    try:
        await asyncio.gather(*[_process(d) for d in domains])
        await update_scan_status(scan_id, "completed")
    except Exception as exc:
        logger.error("Scan %s failed: %s", scan_id, exc)
        await update_scan_status(scan_id, "failed")
