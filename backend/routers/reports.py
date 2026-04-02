"""API routes for report generation and download."""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

from auth import UserProfile, get_user_profile, validate_token
from config import azure_ad, branding as _branding
from database import get_domain_results, get_scan
from models import BrandingConfig, DomainReport
from report.generator import generate_html, generate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


async def _extract_optional_user(authorization: str | None) -> dict | None:
    """Extract user profile from an optional Authorization header.

    Returns a ``prepared_by`` dict or ``None`` if no auth is provided.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):]
    try:
        await validate_token(token)
        profile = await get_user_profile(token)
        return {
            "name": profile.name,
            "title": profile.title,
            "phone": profile.phone,
            "email": profile.email,
        }
    except Exception:
        # Auth is optional -- swallow errors and proceed without user info
        return None


def _get_branding() -> BrandingConfig:
    """Build a BrandingConfig from the current branding singleton."""
    return BrandingConfig(
        company_name=_branding.company_name,
        logo_url=_branding.logo_url,
        primary_color=_branding.primary_color,
        accent_color=_branding.accent_color,
        footer_text=_branding.footer_text,
    )


async def _find_report(scan_id: str, domain: str) -> DomainReport:
    """Look up a completed domain result and convert it to a DomainReport."""
    scan = await get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    results = await get_domain_results(scan_id)
    for r in results:
        if r.get("domain", "").lower() == domain.lower() and r["status"] == "completed" and r.get("raw_data"):
            try:
                return DomainReport(**r["raw_data"])
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Failed to parse report data: {exc}")

    raise HTTPException(status_code=404, detail=f"No completed result found for domain '{domain}' in scan {scan_id}.")


# ---------------------------------------------------------------------------
# PDF / HTML reports
# ---------------------------------------------------------------------------

@router.get("/{scan_id}/{domain}/pdf")
async def download_pdf(scan_id: str, domain: str, authorization: str | None = Header(default=None)):
    """Generate and return a PDF report for a single domain within a scan."""
    try:
        report = await _find_report(scan_id, domain)
        branding = _get_branding()
        prepared_by = await _extract_optional_user(authorization)
        pdf_bytes = generate_pdf(report, branding, prepared_by=prepared_by)
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{domain}_report.pdf"',
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("PDF generation failed for %s/%s", scan_id, domain)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{scan_id}/{domain}/html", response_class=HTMLResponse)
async def download_html(scan_id: str, domain: str, authorization: str | None = Header(default=None)):
    """Return an HTML report for a single domain within a scan."""
    report = await _find_report(scan_id, domain)
    branding = _get_branding()
    prepared_by = await _extract_optional_user(authorization)
    html = generate_html(report, branding, prepared_by=prepared_by)
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Bulk exports
# ---------------------------------------------------------------------------

@router.get("/{scan_id}/export/json")
async def export_json(scan_id: str):
    """Export all completed results for a scan as JSON."""
    scan = await get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    results = await get_domain_results(scan_id)
    reports = []
    for r in results:
        if r["status"] == "completed" and r.get("raw_data"):
            try:
                reports.append(DomainReport(**r["raw_data"]).model_dump(mode="json"))
            except Exception:
                pass

    return JSONResponse(
        content={"scan_id": scan_id, "results": reports},
        headers={"Content-Disposition": f'attachment; filename="scan_{scan_id[:8]}_results.json"'},
    )


@router.get("/{scan_id}/export/csv")
async def export_csv(scan_id: str):
    """Export a summary CSV of all completed results for a scan."""
    scan = await get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    results = await get_domain_results(scan_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Domain",
        "Overall Score",
        "Risk Level",
        "Registration Score",
        "Email Security Score",
        "DNS/Infrastructure Score",
        "Web/SSL Score",
        "General Score",
        "SPF",
        "DMARC",
        "DKIM",
        "HTTPS",
        "SSL Valid",
        "DNSSEC",
        "Redirect to HTTPS",
    ])

    for r in results:
        if r["status"] != "completed" or not r.get("raw_data"):
            continue
        try:
            report = DomainReport(**r["raw_data"])
        except Exception:
            continue

        cs = report.security_assessment.category_scores
        writer.writerow([
            report.domain,
            report.security_assessment.overall_score,
            report.security_assessment.risk_level,
            cs.get("Registration", ""),
            cs.get("Email Security", ""),
            cs.get("DNS/Infrastructure", ""),
            cs.get("Web/SSL", ""),
            cs.get("General", ""),
            "Yes" if report.email_security.spf.record else "No",
            report.email_security.dmarc.policy or "None",
            "Yes" if report.email_security.dkim.found else "No",
            "Yes" if report.http.https_enabled else "No",
            "Yes" if report.ssl.valid else "No",
            "Yes" if report.dnssec.enabled else "No",
            "Yes" if report.http.redirect_to_https else "No",
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="scan_{scan_id[:8]}_summary.csv"'},
    )


# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------

@router.put("/branding")
async def update_branding(body: BrandingConfig):
    """Update the branding configuration used for report generation."""
    _branding.company_name = body.company_name
    _branding.logo_url = body.logo_url
    _branding.primary_color = body.primary_color
    _branding.accent_color = body.accent_color
    _branding.footer_text = body.footer_text
    return {"status": "ok", "branding": body.model_dump()}


@router.get("/branding")
async def get_branding():
    """Return the current branding configuration."""
    return _get_branding().model_dump()
