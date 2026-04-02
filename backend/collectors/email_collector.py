"""SPF and DMARC email security collectors."""

from __future__ import annotations

import logging

import dns.asyncresolver
import dns.exception
import dns.resolver

from models import SpfData, DmarcData

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0


def _txt_strings(rdata) -> str:
    """Join the byte-string parts of a TXT rdata into a single string.

    dnspython splits long TXT records into multiple 255-byte chunks.
    ``rdata.to_text()`` returns them as ``"part1" "part2"`` which breaks
    simple ``strip('\"')`` parsing.  Using ``rdata.strings`` gives us the
    raw parts that we can concatenate cleanly.
    """
    parts = []
    for s in rdata.strings:
        if isinstance(s, bytes):
            parts.append(s.decode("utf-8", errors="replace"))
        else:
            parts.append(str(s))
    return "".join(parts)


async def collect_spf(domain: str) -> SpfData:
    """Collect and analyse the SPF record for a domain."""
    issues: list[str] = []
    record: str | None = None
    valid = False

    try:
        resolver = dns.asyncresolver.Resolver()
        resolver.lifetime = _TIMEOUT
        resolver.timeout = _TIMEOUT
        answers = await resolver.resolve(domain, "TXT")

        spf_records: list[str] = []
        for rdata in answers:
            txt = _txt_strings(rdata)
            if txt.lower().startswith("v=spf1"):
                spf_records.append(txt)

        if len(spf_records) == 0:
            issues.append("No SPF record found. Email spoofing prevention is not configured.")
            return SpfData(record=None, valid=False, issues=issues)

        if len(spf_records) > 1:
            issues.append("Multiple SPF records found. Only one SPF record should exist per domain.")

        record = spf_records[0]
        valid = True

        # Check for dangerous +all
        if "+all" in record:
            issues.append(
                "SPF record contains '+all', which allows any server to send email on behalf of this domain. "
                "This effectively disables SPF protection."
            )
            valid = False

        # Check for soft fail (~all) vs hard fail (-all)
        if "~all" in record:
            issues.append(
                "SPF record uses '~all' (soft fail). Consider using '-all' (hard fail) for stronger protection."
            )

        # Check if the record ends with a proper mechanism
        if not any(record.rstrip().endswith(suffix) for suffix in ["-all", "~all", "+all", "?all", "redirect="]):
            issues.append("SPF record does not end with an 'all' mechanism or redirect. This may cause unexpected behaviour.")

        # Hint about DNS lookup limits
        include_count = record.lower().count("include:")
        a_count = record.lower().count(" a:")
        mx_count = record.lower().count(" mx:")
        lookup_count = include_count + a_count + mx_count
        if lookup_count > 8:
            issues.append(
                f"SPF record has approximately {lookup_count} DNS-lookup mechanisms. "
                "SPF allows a maximum of 10 DNS lookups; exceeding this may cause delivery failures."
            )

    except dns.resolver.NXDOMAIN:
        issues.append("Domain does not exist in DNS.")
    except dns.resolver.NoAnswer:
        issues.append("No TXT records found for domain; SPF is not configured.")
    except dns.exception.Timeout:
        issues.append("DNS query timed out when checking SPF record.")
    except Exception as exc:
        logger.warning("SPF check failed for %s: %s", domain, exc)
        issues.append(f"SPF check encountered an error: {exc}")

    return SpfData(record=record, valid=valid, issues=issues)


async def collect_dmarc(domain: str) -> DmarcData:
    """Collect and analyse the DMARC record for a domain."""
    issues: list[str] = []
    record: str | None = None
    policy: str | None = None
    valid = False

    dmarc_domain = f"_dmarc.{domain}"

    try:
        resolver = dns.asyncresolver.Resolver()
        resolver.lifetime = _TIMEOUT
        resolver.timeout = _TIMEOUT
        answers = await resolver.resolve(dmarc_domain, "TXT")

        dmarc_records: list[str] = []
        for rdata in answers:
            txt = _txt_strings(rdata)
            if txt.lower().startswith("v=dmarc1"):
                dmarc_records.append(txt)

        if len(dmarc_records) == 0:
            issues.append("No DMARC record found. Email authentication reporting is not configured.")
            return DmarcData(record=None, policy=None, valid=False, issues=issues)

        if len(dmarc_records) > 1:
            issues.append("Multiple DMARC records found. Only one DMARC record should exist.")

        record = dmarc_records[0]
        valid = True

        # Parse policy
        tags = {}
        for part in record.split(";"):
            part = part.strip()
            if "=" in part:
                key, _, val = part.partition("=")
                tags[key.strip().lower()] = val.strip().lower()

        policy = tags.get("p")

        if policy is None:
            issues.append("DMARC record is missing the required 'p' (policy) tag.")
            valid = False
        elif policy == "none":
            issues.append(
                "DMARC policy is set to 'none', which only monitors but does not block "
                "spoofed emails. Consider upgrading to 'quarantine' or 'reject'."
            )
        elif policy == "quarantine":
            pass  # Acceptable
        elif policy == "reject":
            pass  # Best practice
        else:
            issues.append(f"DMARC policy '{policy}' is not a recognised value.")
            valid = False

        # Check for reporting addresses
        if "rua" not in tags:
            issues.append(
                "DMARC record does not include a 'rua' (aggregate report) address. "
                "Adding one allows you to receive reports about email authentication results."
            )

        # Check sub-domain policy
        if "sp" not in tags and policy in ("quarantine", "reject"):
            issues.append(
                "Consider adding an 'sp' (sub-domain policy) tag to extend DMARC protection to sub-domains."
            )

    except dns.resolver.NXDOMAIN:
        issues.append("No DMARC record found (NXDOMAIN). Email authentication reporting is not configured.")
    except dns.resolver.NoAnswer:
        issues.append("No DMARC record found. Email authentication reporting is not configured.")
    except dns.exception.Timeout:
        issues.append("DNS query timed out when checking DMARC record.")
    except Exception as exc:
        logger.warning("DMARC check failed for %s: %s", domain, exc)
        issues.append(f"DMARC check encountered an error: {exc}")

    return DmarcData(record=record, policy=policy, valid=valid, issues=issues)
