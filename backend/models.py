"""Pydantic models and schemas for the ATS Domain Review API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

FREE_EMAIL_DOMAINS: set[str] = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "yahoo.co.in",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "aol.com", "icloud.com", "me.com", "mac.com",
    "mail.com", "email.com", "inbox.com", "zoho.com",
    "proton.me", "protonmail.com", "tutanota.com", "tutamail.com",
    "yandex.com", "yandex.ru", "gmx.com", "gmx.net",
    "fastmail.com", "hushmail.com", "mailinator.com",
    "comcast.net", "sbcglobal.net", "att.net", "verizon.net",
    "cox.net", "charter.net", "earthlink.net", "juno.com",
    "bellsouth.net", "optonline.net", "frontier.com",
}


def is_free_email_domain(domain: str) -> bool:
    """Return True if the domain is a well-known free email provider."""
    return domain.lower() in FREE_EMAIL_DOMAINS


class DomainInput(BaseModel):
    """Request body for submitting domains for scanning."""

    domains: list[str]

    @field_validator("domains", mode="before")
    @classmethod
    def validate_domains(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one domain is required")
        cleaned: list[str] = []
        domain_pattern = re.compile(
            r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
        )
        for raw in v:
            domain = raw.strip().lower().rstrip(".")
            # Strip protocol prefixes if present
            domain = re.sub(r"^https?://", "", domain)
            # Strip paths
            domain = domain.split("/")[0]
            if not domain_pattern.match(domain):
                raise ValueError(f"Invalid domain format: {raw}")
            cleaned.append(domain)
        return cleaned


class EmailInput(BaseModel):
    """Request body for submitting email addresses."""

    emails: list[str]

    @field_validator("emails", mode="before")
    @classmethod
    def validate_emails(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one email address is required")
        cleaned: list[str] = []
        email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        for raw in v:
            email = raw.strip().lower()
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email format: {raw}")
            cleaned.append(email)
        return cleaned


# ---------------------------------------------------------------------------
# Collector data models
# ---------------------------------------------------------------------------

class WhoisData(BaseModel):
    """WHOIS lookup results."""

    registrar: Optional[str] = None
    creation_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    name_servers: list[str] = []
    registrant: Optional[str] = None
    privacy_protected: bool = False


class DnsData(BaseModel):
    """DNS record lookup results."""

    a_records: list[str] = []
    aaaa_records: list[str] = []
    cname_records: list[str] = []
    mx_records: list[str] = []
    ns_records: list[str] = []
    txt_records: list[str] = []


class SpfData(BaseModel):
    """SPF record analysis results."""

    record: Optional[str] = None
    valid: bool = False
    issues: list[str] = []


class DmarcData(BaseModel):
    """DMARC record analysis results."""

    record: Optional[str] = None
    policy: Optional[str] = None
    valid: bool = False
    issues: list[str] = []


class DkimData(BaseModel):
    """DKIM record analysis results."""

    found: bool = False
    selectors_checked: list[str] = []
    selectors_found: list[str] = []
    records: dict[str, str] = {}


class DnssecData(BaseModel):
    """DNSSEC validation results."""

    enabled: bool = False
    details: str = ""


class SslData(BaseModel):
    """SSL/TLS certificate analysis results."""

    valid: bool = False
    issuer: Optional[str] = None
    subject: Optional[str] = None
    not_before: Optional[datetime] = None
    not_after: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    issues: list[str] = []


class HttpData(BaseModel):
    """HTTP/HTTPS connectivity results."""

    reachable: bool = False
    https_enabled: bool = False
    redirect_to_https: bool = False
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    site_title: Optional[str] = None


class EmailSecurityData(BaseModel):
    """Combined email security assessment."""

    spf: SpfData = SpfData()
    dmarc: DmarcData = DmarcData()
    dkim: DkimData = DkimData()
    mx_records: list[str] = []
    overall_email_score: int = 0
    issues: list[str] = []
    recommendations: list[str] = []


class Implication(BaseModel):
    """A single finding with its business implication."""

    finding: str
    implication: str
    severity: str = "info"  # "good", "info", "warning", "critical"


class SecurityAssessment(BaseModel):
    """Overall security scoring and assessment."""

    overall_score: int = 0
    risk_level: str = "Poor"
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    implications: list[Implication] = []
    category_scores: dict[str, int] = {}


class DomainReport(BaseModel):
    """Complete domain assessment report."""

    domain: str
    scan_id: str
    timestamp: datetime
    is_free_domain: bool = False
    source_emails: list[str] = []
    whois: WhoisData = WhoisData()
    dns: DnsData = DnsData()
    email_security: EmailSecurityData = EmailSecurityData()
    dnssec: DnssecData = DnssecData()
    ssl: SslData = SslData()
    http: HttpData = HttpData()
    security_assessment: SecurityAssessment = SecurityAssessment()


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------

class ScanResponse(BaseModel):
    """Response after initiating a scan."""

    scan_id: str
    status: str
    domains: list[str]


class ScanStatus(BaseModel):
    """Current status of a scan."""

    scan_id: str
    status: str
    total: int
    completed: int
    results: Optional[list[DomainReport]] = None


class BrandingConfig(BaseModel):
    """Branding configuration for reports."""

    company_name: str = "ATS Domain Review"
    logo_url: str = ""
    primary_color: str = "#1a365d"
    accent_color: str = "#2b6cb0"
    footer_text: str = "Confidential - Prepared by ATS Domain Review"
