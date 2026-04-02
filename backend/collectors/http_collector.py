"""HTTP/HTTPS connectivity collector."""

from __future__ import annotations

import html as html_mod
import logging
import re
import time

import httpx

from models import HttpData

logger = logging.getLogger(__name__)

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _extract_title(resp: httpx.Response) -> str | None:
    """Pull the <title> text from an HTML response."""
    content_type = resp.headers.get("content-type", "")
    if "html" not in content_type:
        return None
    try:
        # Read enough to find the <title> even on JS-heavy pages
        text = resp.text[:200_000]
        match = _TITLE_RE.search(text)
        if match:
            title = match.group(1).strip()
            # Decode HTML entities and collapse whitespace
            title = html_mod.unescape(title)
            title = re.sub(r"\s+", " ", title)
            return title if title else None
    except Exception:
        pass
    return None


async def collect_http(domain: str, timeout: int = 10) -> HttpData:
    """Check HTTP and HTTPS connectivity for a domain.

    Tests both ``http://`` and ``https://`` endpoints, following up to
    5 redirects.  Records whether the site redirects HTTP to HTTPS and
    measures the response time.

    Args:
        domain: The domain name to check.
        timeout: Maximum seconds for each request.

    Returns:
        HttpData with reachability, HTTPS, redirect, and timing information.
    """
    reachable = False
    https_enabled = False
    redirect_to_https = False
    status_code: int | None = None
    response_time_ms: float | None = None
    site_title: str | None = None

    transport = httpx.AsyncHTTPTransport(retries=0)
    async with httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        max_redirects=5,
        verify=False,  # We check SSL separately; here we just want connectivity info
    ) as client:
        # Try HTTPS first
        try:
            start = time.monotonic()
            resp = await client.get(f"https://{domain}")
            elapsed = (time.monotonic() - start) * 1000
            https_enabled = True
            reachable = True
            status_code = resp.status_code
            response_time_ms = round(elapsed, 2)
            site_title = _extract_title(resp)
        except Exception:
            # HTTPS not reachable, try HTTP
            https_enabled = False

        # Try HTTP to check for redirect
        try:
            start = time.monotonic()
            resp_http = await client.get(f"http://{domain}")
            elapsed_http = (time.monotonic() - start) * 1000
            reachable = True

            if status_code is None:
                status_code = resp_http.status_code
                response_time_ms = round(elapsed_http, 2)
            if site_title is None:
                site_title = _extract_title(resp_http)

            # Check if any redirect in the chain went to HTTPS
            if resp_http.url and str(resp_http.url).startswith("https://"):
                redirect_to_https = True
            for history_resp in resp_http.history:
                location = history_resp.headers.get("location", "")
                if location.startswith("https://"):
                    redirect_to_https = True
                    break

        except Exception:
            # HTTP also not reachable
            pass

    return HttpData(
        reachable=reachable,
        https_enabled=https_enabled,
        redirect_to_https=redirect_to_https,
        status_code=status_code,
        response_time_ms=response_time_ms,
        site_title=site_title,
    )
