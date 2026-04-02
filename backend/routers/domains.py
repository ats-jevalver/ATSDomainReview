"""API routes for domain scan operations."""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from analyzer import run_scan
from database import (
    create_scan,
    get_domain_results,
    get_latest_domain_result,
    get_scan,
    get_scan_progress,
)
from models import DomainInput, EmailInput, DomainReport, ScanResponse, ScanStatus, is_free_email_domain

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.post("/scan", response_model=ScanResponse)
async def start_scan(body: DomainInput, background_tasks: BackgroundTasks):
    """Start a new domain health scan.

    Accepts a JSON body with a list of domain names, creates a scan record,
    and begins processing in the background.

    Returns the scan ID that can be used to poll for status.
    """
    scan_id = str(uuid.uuid4())
    await create_scan(scan_id)
    background_tasks.add_task(run_scan, scan_id, body.domains)
    return ScanResponse(scan_id=scan_id, status="pending", domains=body.domains)


@router.post("/scan/csv", response_model=ScanResponse)
async def start_scan_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Start a scan by uploading a CSV file containing domain names.

    The CSV should have domain names in the first column. A header row
    is expected and will be skipped if the first cell does not look like
    a valid domain.
    """
    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    domains: list[str] = []
    for row in reader:
        if not row:
            continue
        candidate = row[0].strip().lower()
        if not candidate or candidate in ("domain", "domains", "hostname", "host"):
            continue
        domains.append(candidate)

    if not domains:
        raise HTTPException(status_code=400, detail="No valid domains found in the uploaded CSV.")

    # Validate through the model
    validated = DomainInput(domains=domains)

    scan_id = str(uuid.uuid4())
    await create_scan(scan_id)
    background_tasks.add_task(run_scan, scan_id, validated.domains)
    return ScanResponse(scan_id=scan_id, status="pending", domains=validated.domains)


@router.get("/scan/{scan_id}", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """Get the current status of a scan including progress counts."""
    scan = await get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    progress = await get_scan_progress(scan_id)

    results = None
    if scan["status"] == "completed":
        raw_results = await get_domain_results(scan_id)
        results = []
        for r in raw_results:
            if r.get("raw_data") and r["status"] == "completed":
                try:
                    results.append(DomainReport(**r["raw_data"]))
                except Exception:
                    pass

    return ScanStatus(
        scan_id=scan_id,
        status=scan["status"],
        total=progress["total"],
        completed=progress["completed"],
        results=results,
    )


@router.get("/scan/{scan_id}/results")
async def get_scan_results(scan_id: str):
    """Get all domain results for a completed scan."""
    scan = await get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found.")

    raw_results = await get_domain_results(scan_id)
    reports: list[DomainReport] = []
    for r in raw_results:
        if r.get("raw_data") and r["status"] == "completed":
            try:
                reports.append(DomainReport(**r["raw_data"]))
            except Exception:
                pass

    return {"scan_id": scan_id, "status": scan["status"], "results": [r.model_dump() for r in reports]}


@router.post("/scan/emails", response_model=ScanResponse)
async def start_scan_from_emails(body: EmailInput, background_tasks: BackgroundTasks):
    """Parse email addresses, extract unique domains, and start a scan.

    Free email domains (gmail.com, outlook.com, etc.) are still included
    in the scan but flagged so the report can show a business-email advisory.
    The source email addresses are attached to each domain result.
    """
    # Group emails by domain
    domain_emails: dict[str, list[str]] = {}
    for email in body.emails:
        _, domain = email.rsplit("@", 1)
        domain_emails.setdefault(domain, []).append(email)

    domains = list(domain_emails.keys())
    if not domains:
        raise HTTPException(status_code=400, detail="No domains extracted from the email list.")

    scan_id = str(uuid.uuid4())
    await create_scan(scan_id)
    background_tasks.add_task(
        run_scan, scan_id, domains,
        email_map=domain_emails,
    )
    return ScanResponse(scan_id=scan_id, status="pending", domains=domains)


@router.get("/{domain}/latest")
async def get_latest_for_domain(domain: str):
    """Get the most recent scan result for a specific domain."""
    result = await get_latest_domain_result(domain.lower())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No results found for domain: {domain}")

    if result.get("raw_data") and result["status"] == "completed":
        try:
            report = DomainReport(**result["raw_data"])
            return report.model_dump()
        except Exception:
            pass

    return result
