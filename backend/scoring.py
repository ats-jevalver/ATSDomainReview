"""Health and security scoring engine for domain assessments."""

from __future__ import annotations

from datetime import datetime, timezone

from models import (
    DkimData,
    DmarcData,
    DnsData,
    DnssecData,
    HttpData,
    Implication,
    SecurityAssessment,
    SpfData,
    SslData,
    WhoisData,
)


def calculate_score(
    whois: WhoisData,
    dns: DnsData,
    spf: SpfData,
    dmarc: DmarcData,
    dkim: DkimData,
    dnssec: DnssecData,
    ssl: SslData,
    http: HttpData,
) -> SecurityAssessment:
    """Calculate the overall domain health/security score.

    Evaluates five categories -- Registration, Email Security,
    DNS/Infrastructure, Web/SSL, and General -- returning a
    SecurityAssessment with an overall score (0-100), risk level,
    strengths, weaknesses, and actionable recommendations.

    Args:
        whois: WHOIS data for the domain.
        dns: DNS record data.
        spf: SPF analysis data.
        dmarc: DMARC analysis data.
        dkim: DKIM analysis data.
        dnssec: DNSSEC data.
        ssl: SSL certificate data.
        http: HTTP connectivity data.

    Returns:
        SecurityAssessment with scoring breakdown and guidance.
    """
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    implications: list[Implication] = []

    # -----------------------------------------------------------------------
    # Registration (15 points)
    # -----------------------------------------------------------------------
    registration_score = 0

    # Domain registered and not expired (5 pts)
    now = datetime.now(timezone.utc)
    if whois.creation_date is not None:
        if whois.expiration_date is None or whois.expiration_date.replace(tzinfo=timezone.utc) > now:
            registration_score += 5
            strengths.append("Domain is registered and currently active.")
        else:
            weaknesses.append("Domain registration has expired.")
            recommendations.append(
                "Renew your domain registration immediately to prevent service disruptions and potential hijacking."
            )
    else:
        weaknesses.append("Unable to verify domain registration details.")
        recommendations.append(
            "Ensure your WHOIS information is accessible so clients and partners can verify domain ownership."
        )

    # Expiration > 90 days (5/3/0 pts)
    if whois.expiration_date is not None:
        exp = whois.expiration_date.replace(tzinfo=timezone.utc) if whois.expiration_date.tzinfo is None else whois.expiration_date
        days_to_expiry = (exp - now).days
        if days_to_expiry > 90:
            registration_score += 5
            strengths.append(f"Domain registration is valid for {days_to_expiry} more days.")
        elif days_to_expiry > 30:
            registration_score += 3
            weaknesses.append(f"Domain expires in {days_to_expiry} days.")
            recommendations.append(
                "Your domain expires within 90 days. Renew it soon and consider enabling auto-renewal."
            )
        else:
            weaknesses.append(f"Domain expires in only {days_to_expiry} days.")
            recommendations.append(
                "Your domain is close to expiration. Renew it immediately to avoid losing ownership."
            )

    # Registrar info available (5 pts)
    if whois.registrar:
        registration_score += 5
        strengths.append(f"Registrar information is available ({whois.registrar}).")
    else:
        weaknesses.append("Registrar information is not available.")

    # -----------------------------------------------------------------------
    # Email Security (30 points)
    # -----------------------------------------------------------------------
    email_score = 0

    # MX records present (5 pts)
    if dns.mx_records:
        email_score += 5
        strengths.append("Mail exchange (MX) records are configured for email delivery.")
    else:
        weaknesses.append("No MX records found; the domain cannot receive email.")
        recommendations.append(
            "Set up MX records if you intend to use email with this domain."
        )

    # SPF present (5 pts)
    if spf.record:
        email_score += 5
        strengths.append("An SPF record is published, helping prevent email spoofing.")
    else:
        weaknesses.append("No SPF record found.")
        recommendations.append(
            "Publish an SPF record to specify which mail servers are authorised to send email for your domain. "
            "This helps prevent spoofing and improves email deliverability."
        )

    # SPF valid / no +all (5 pts)
    if spf.record and spf.valid:
        email_score += 5
    elif spf.record and not spf.valid:
        weaknesses.append("SPF record has configuration issues.")
        recommendations.append(
            "Review and correct your SPF record. Avoid using '+all' and ensure the record ends with '-all' or '~all'."
        )

    # DMARC present (5 pts)
    if dmarc.record:
        email_score += 5
        strengths.append("A DMARC record is published for email authentication monitoring.")
    else:
        weaknesses.append("No DMARC record found.")
        recommendations.append(
            "Add a DMARC record (e.g. _dmarc.yourdomain.com) to monitor and control how "
            "unauthenticated emails from your domain are handled."
        )

    # DMARC policy reject/quarantine (5/2 pts)
    if dmarc.policy in ("reject", "quarantine"):
        email_score += 5
        strengths.append(f"DMARC policy is set to '{dmarc.policy}', actively protecting against spoofing.")
    elif dmarc.policy == "none":
        email_score += 2
        weaknesses.append("DMARC policy is set to 'none' (monitoring only).")
        recommendations.append(
            "Upgrade your DMARC policy from 'none' to 'quarantine' or 'reject' to actively block spoofed emails."
        )

    # DKIM detected (5 pts)
    if dkim.found:
        email_score += 5
        strengths.append(
            f"DKIM signing is configured (selector(s): {', '.join(dkim.selectors_found)})."
        )
    else:
        weaknesses.append("No DKIM records were detected for common selectors.")
        recommendations.append(
            "Configure DKIM signing for your outbound email. DKIM adds a digital signature "
            "that verifies messages have not been altered in transit."
        )

    # -----------------------------------------------------------------------
    # DNS / Infrastructure (15 points)
    # -----------------------------------------------------------------------
    dns_score = 0

    # DNS resolves (5 pts)
    if dns.a_records or dns.aaaa_records or dns.cname_records:
        dns_score += 5
        strengths.append("Domain resolves in DNS.")
    else:
        weaknesses.append("Domain does not resolve to any address records.")
        recommendations.append(
            "Verify your DNS configuration. The domain should have at least an A or AAAA record."
        )

    # Multiple nameservers (5 pts)
    if len(dns.ns_records) >= 2:
        dns_score += 5
        strengths.append(f"Multiple nameservers configured ({len(dns.ns_records)}).")
    elif len(dns.ns_records) == 1:
        weaknesses.append("Only one nameserver is configured.")
        recommendations.append(
            "Add at least one additional nameserver for redundancy. If your primary nameserver "
            "goes down, email and website services will be unavailable."
        )
    else:
        weaknesses.append("No nameserver records found.")

    # DNSSEC enabled (5 pts)
    if dnssec.enabled:
        dns_score += 5
        strengths.append("DNSSEC is enabled, protecting against DNS spoofing.")
    else:
        weaknesses.append("DNSSEC is not enabled.")
        recommendations.append(
            "Enable DNSSEC to add cryptographic verification to your DNS records, "
            "protecting visitors from being redirected to malicious sites."
        )

    # -----------------------------------------------------------------------
    # Web / SSL (25 points)
    # -----------------------------------------------------------------------
    web_score = 0

    # Website reachable (5 pts)
    if http.reachable:
        web_score += 5
        strengths.append("Website is reachable.")
    else:
        weaknesses.append("Website is not reachable via HTTP or HTTPS.")
        recommendations.append(
            "Ensure your web server is running and accessible. If the domain is not intended to host a website, "
            "consider publishing a landing page or redirect."
        )

    # HTTPS enabled (5 pts)
    if http.https_enabled:
        web_score += 5
        strengths.append("HTTPS is enabled.")
    else:
        weaknesses.append("HTTPS is not available.")
        recommendations.append(
            "Enable HTTPS by installing an SSL/TLS certificate. Free certificates are available from Let's Encrypt."
        )

    # SSL cert valid (5 pts)
    if ssl.valid:
        web_score += 5
        strengths.append("SSL/TLS certificate is valid.")
    else:
        if ssl.issues:
            for issue in ssl.issues:
                weaknesses.append(f"SSL issue: {issue}")
        else:
            weaknesses.append("SSL/TLS certificate is invalid or missing.")
        recommendations.append(
            "Ensure your SSL/TLS certificate is valid and properly installed. "
            "An invalid certificate will display browser warnings to your visitors."
        )

    # SSL cert not expiring within 30 days (5 pts)
    if ssl.valid and ssl.days_until_expiry is not None and ssl.days_until_expiry > 30:
        web_score += 5
        strengths.append(f"SSL certificate has {ssl.days_until_expiry} days remaining.")
    elif ssl.valid and ssl.days_until_expiry is not None and ssl.days_until_expiry <= 30:
        weaknesses.append(f"SSL certificate expires in {ssl.days_until_expiry} days.")
        recommendations.append(
            "Renew your SSL/TLS certificate soon. Consider automating renewals to prevent lapses."
        )

    # Redirects HTTP to HTTPS (5 pts)
    if http.redirect_to_https:
        web_score += 5
        strengths.append("HTTP traffic is automatically redirected to HTTPS.")
    elif http.https_enabled and http.reachable:
        weaknesses.append("HTTP does not redirect to HTTPS.")
        recommendations.append(
            "Configure your web server to redirect all HTTP requests to HTTPS "
            "so that visitors always use a secure connection."
        )

    # -----------------------------------------------------------------------
    # General (15 points)
    # -----------------------------------------------------------------------
    general_score = 0

    # Response time < 2s (5 pts)
    if http.response_time_ms is not None and http.response_time_ms < 2000:
        general_score += 5
        strengths.append(f"Website responds quickly ({http.response_time_ms:.0f} ms).")
    elif http.response_time_ms is not None:
        weaknesses.append(f"Website response time is slow ({http.response_time_ms:.0f} ms).")
        recommendations.append(
            "Investigate your website's performance. Slow load times can affect user experience "
            "and search engine rankings."
        )

    # No obvious misconfigurations (5 pts)
    misconfiguration_count = len([i for i in spf.issues if i]) + len([i for i in dmarc.issues if i])
    if misconfiguration_count == 0:
        general_score += 5
        strengths.append("No obvious email authentication misconfigurations detected.")
    else:
        weaknesses.append(f"{misconfiguration_count} email configuration issue(s) detected.")

    # Overall consistency (5 pts)
    # Award if the domain has both web and email set up consistently
    has_web = http.reachable and http.https_enabled and ssl.valid
    has_email = bool(dns.mx_records) and spf.record is not None and dmarc.record is not None
    if has_web and has_email:
        general_score += 5
        strengths.append("Domain has a consistent configuration across web and email services.")
    elif has_web or has_email:
        general_score += 2
        weaknesses.append("Domain configuration is partially complete.")
        recommendations.append(
            "For best protection, ensure both your website (HTTPS, valid certificate) and "
            "email (SPF, DKIM, DMARC) are fully configured."
        )
    else:
        weaknesses.append("Neither web nor email services appear to be fully configured.")

    # -----------------------------------------------------------------------
    # Implications -- concise, plain-language business impact summaries.
    # Related findings are grouped into single sentences rather than
    # listed one-by-one.
    # -----------------------------------------------------------------------

    # --- Registration ---
    if whois.expiration_date is not None:
        exp = whois.expiration_date.replace(tzinfo=timezone.utc) if whois.expiration_date.tzinfo is None else whois.expiration_date
        dte = (exp - now).days
        if dte <= 30:
            implications.append(Implication(
                finding=f"Domain expires in {dte} days",
                implication="The domain could lapse at any moment. If it expires, email, your website, and all connected services go offline. Renew immediately.",
                severity="critical",
            ))
        elif dte <= 90:
            implications.append(Implication(
                finding=f"Domain expires in {dte} days",
                implication="Expiration is approaching. Enable auto-renewal to avoid an accidental lapse that could take services offline.",
                severity="warning",
            ))
    elif whois.creation_date is None:
        implications.append(Implication(
            finding="Domain registration could not be verified",
            implication="WHOIS data is unavailable. Confirm the domain is registered and will not expire unexpectedly.",
            severity="warning",
        ))

    # --- Email authentication (combined) ---
    has_spf = bool(spf.record and spf.valid)
    has_dmarc = bool(dmarc.record and dmarc.valid)
    has_dkim = dkim.found
    missing_email: list[str] = []
    if not has_spf:
        missing_email.append("SPF")
    if not has_dmarc:
        missing_email.append("DMARC")
    if not has_dkim:
        missing_email.append("DKIM")

    if not missing_email:
        implications.append(Implication(
            finding="SPF, DMARC, and DKIM are all configured",
            implication="Email authentication is fully in place. This protects against spoofing and helps ensure your emails reach recipients' inboxes.",
            severity="good",
        ))
    elif len(missing_email) == 3:
        implications.append(Implication(
            finding="No SPF, DMARC, or DKIM configured",
            implication="Anyone can send email that appears to come from this domain. This makes phishing easy, damages brand trust, and causes legitimate emails to land in spam.",
            severity="critical",
        ))
    else:
        missing_str = " and ".join(missing_email)
        implications.append(Implication(
            finding=f"Missing {missing_str}",
            implication=f"Without {missing_str}, email deliverability will suffer and the domain is more vulnerable to spoofing. Configuring the missing record(s) closes the gap.",
            severity="warning" if len(missing_email) == 1 else "critical",
        ))

    if dmarc.policy == "none" and dmarc.record:
        implications.append(Implication(
            finding="DMARC policy is monitor-only",
            implication="DMARC is set to 'none', which reports on spoofing but does not block it. Upgrade to 'quarantine' or 'reject' once you have reviewed the reports.",
            severity="warning",
        ))

    if spf.record and not spf.valid:
        implications.append(Implication(
            finding="SPF record has configuration issues",
            implication="A broken SPF record can cause legitimate emails to be rejected. Review and correct the record to restore deliverability.",
            severity="warning",
        ))

    # --- MX ---
    if not dns.mx_records:
        implications.append(Implication(
            finding="No MX records",
            implication="This domain cannot receive email. If email is intended, MX records need to be added. If not, no action is needed.",
            severity="info",
        ))

    # --- DNS infrastructure ---
    if len(dns.ns_records) == 1:
        implications.append(Implication(
            finding="Single nameserver",
            implication="If that nameserver goes down, the entire domain goes offline -- email, website, everything. Add a second nameserver for redundancy.",
            severity="warning",
        ))

    if not dnssec.enabled:
        implications.append(Implication(
            finding="DNSSEC is not enabled",
            implication="DNS responses are not cryptographically signed. This leaves visitors vulnerable to being redirected to malicious sites. Consider enabling DNSSEC with your registrar.",
            severity="info",
        ))

    # --- Web / SSL (combined) ---
    if not http.reachable:
        implications.append(Implication(
            finding="Website is not reachable",
            implication="No web server responded. If this domain should host a website, it is currently down. If the domain is email-only, no action is needed.",
            severity="info",
        ))
    else:
        web_issues: list[str] = []
        if not http.https_enabled:
            web_issues.append("no HTTPS")
        elif not ssl.valid:
            web_issues.append("an invalid SSL certificate")
        if http.https_enabled and not http.redirect_to_https:
            web_issues.append("no HTTP-to-HTTPS redirect")
        if ssl.valid and ssl.days_until_expiry is not None and ssl.days_until_expiry <= 30:
            web_issues.append(f"an SSL certificate expiring in {ssl.days_until_expiry} days")

        if not web_issues:
            implications.append(Implication(
                finding="Website and SSL are healthy",
                implication="The site is reachable over HTTPS with a valid certificate. Visitors see no security warnings and search engines rank the site favourably.",
                severity="good",
            ))
        else:
            issue_str = ", ".join(web_issues)
            has_critical = "no HTTPS" in issue_str or "invalid SSL" in issue_str
            implications.append(Implication(
                finding=f"Website has {issue_str}",
                implication=f"Visitors may see browser security warnings or have their data exposed. Fixing {issue_str} will protect visitors and improve search rankings.",
                severity="critical" if has_critical else "warning",
            ))

    # -----------------------------------------------------------------------
    # Aggregate
    # -----------------------------------------------------------------------
    overall_score = registration_score + email_score + dns_score + web_score + general_score

    if overall_score >= 70:
        risk_level = "Good"
    elif overall_score >= 40:
        risk_level = "Moderate"
    else:
        risk_level = "Poor"

    category_scores = {
        "Registration": registration_score,
        "Email Security": email_score,
        "DNS/Infrastructure": dns_score,
        "Web/SSL": web_score,
        "General": general_score,
    }

    return SecurityAssessment(
        overall_score=overall_score,
        risk_level=risk_level,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        implications=implications,
        category_scores=category_scores,
    )
