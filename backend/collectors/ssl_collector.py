"""SSL/TLS certificate collector."""

from __future__ import annotations

import asyncio
import logging
import ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from models import SslData

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=10)


def _get_certificate_info(domain: str, timeout: int = 10) -> SslData:
    """Connect to a domain on port 443 and extract certificate details (sync)."""
    issues: list[str] = []
    try:
        ctx = ssl.create_default_context()
        conn = ctx.wrap_socket(
            __import__("socket").create_connection((domain, 443), timeout=timeout),
            server_hostname=domain,
        )
        try:
            der_cert = conn.getpeercert(binary_form=True)
            if der_cert is None:
                return SslData(valid=False, issues=["No certificate returned by server."])

            cert = x509.load_der_x509_certificate(der_cert, default_backend())

            # Extract issuer
            issuer_parts = []
            for attr in cert.issuer:
                issuer_parts.append(f"{attr.oid._name}={attr.value}")
            issuer_str = ", ".join(issuer_parts)

            # Extract subject
            subject_parts = []
            for attr in cert.subject:
                subject_parts.append(f"{attr.oid._name}={attr.value}")
            subject_str = ", ".join(subject_parts)

            not_before = cert.not_valid_before_utc
            not_after = cert.not_valid_after_utc
            now = datetime.now(timezone.utc)
            days_until_expiry = (not_after - now).days

            valid = True

            if now < not_before:
                issues.append("Certificate is not yet valid (start date is in the future).")
                valid = False

            if now > not_after:
                issues.append("Certificate has expired.")
                valid = False

            if days_until_expiry <= 30 and valid:
                issues.append(
                    f"Certificate expires in {days_until_expiry} days. Renew it soon to avoid disruptions."
                )

            if days_until_expiry <= 7 and valid:
                issues.append("Certificate is critically close to expiration.")

            return SslData(
                valid=valid,
                issuer=issuer_str,
                subject=subject_str,
                not_before=not_before,
                not_after=not_after,
                days_until_expiry=days_until_expiry,
                issues=issues,
            )
        finally:
            conn.close()

    except ssl.SSLCertVerificationError as exc:
        issues.append(f"SSL certificate verification failed: {exc}")
        return SslData(valid=False, issues=issues)
    except ssl.SSLError as exc:
        issues.append(f"SSL error: {exc}")
        return SslData(valid=False, issues=issues)
    except ConnectionRefusedError:
        issues.append("Connection refused on port 443. HTTPS may not be enabled.")
        return SslData(valid=False, issues=issues)
    except TimeoutError:
        issues.append("Connection to port 443 timed out.")
        return SslData(valid=False, issues=issues)
    except OSError as exc:
        issues.append(f"Network error connecting to port 443: {exc}")
        return SslData(valid=False, issues=issues)
    except Exception as exc:
        logger.error("SSL check failed for %s: %s", domain, exc)
        issues.append(f"Unexpected error during SSL check: {exc}")
        return SslData(valid=False, issues=issues)


async def collect_ssl(domain: str, timeout: int = 10) -> SslData:
    """Collect SSL/TLS certificate data for a domain.

    Connects to port 443, retrieves the certificate, and extracts
    issuer, subject, validity dates, and potential issues.

    Args:
        domain: The domain name to check.
        timeout: Maximum seconds for the connection.

    Returns:
        SslData with certificate details and any issues found.
    """
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_executor, _get_certificate_info, domain, timeout),
            timeout=timeout + 5,
        )
    except asyncio.TimeoutError:
        return SslData(valid=False, issues=["SSL certificate check timed out."])
    except Exception as exc:
        logger.error("SSL collection error for %s: %s", domain, exc)
        return SslData(valid=False, issues=[f"SSL check failed: {exc}"])
