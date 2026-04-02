"""HTML and PDF report generation."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from jinja2 import Environment, FileSystemLoader

from models import BrandingConfig, DomainReport

_TEMPLATE_DIR = Path(__file__).parent / "templates"

# fpdf2's built-in Helvetica only supports latin-1.  Replace common
# Unicode characters that appear in generated text with safe equivalents.
_UNICODE_REPLACEMENTS = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote / apostrophe
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u2022": "-",    # bullet
    "\u00a0": " ",    # non-breaking space
    "\u200b": "",     # zero-width space
}


def _safe(text: str) -> str:
    """Replace Unicode characters that Helvetica cannot render."""
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    # Fallback: replace anything remaining outside latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")
_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def generate_html(report: DomainReport, branding: BrandingConfig, prepared_by: dict | None = None) -> str:
    """Render a domain report as a complete HTML document."""
    template = _env.get_template("report.html")
    return template.render(report=report, branding=branding, prepared_by=prepared_by)


# ---------------------------------------------------------------------------
# PDF generation using fpdf2 (pure Python, no system dependencies)
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert a hex colour string to an (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


class _ReportPDF(FPDF):
    """Custom FPDF subclass with header/footer branding."""

    def __init__(self, branding: BrandingConfig):
        super().__init__()
        self.branding = branding
        self._primary = _hex_to_rgb(branding.primary_color)
        self._accent = _hex_to_rgb(branding.accent_color)
        self._cover_page = False  # suppress header/footer on cover

    def cell(self, w=None, h=None, text="", *args, **kwargs):
        return super().cell(w, h, _safe(str(text)), *args, **kwargs)

    def multi_cell(self, w, h=None, text="", *args, **kwargs):
        return super().multi_cell(w, h, _safe(str(text)), *args, **kwargs)

    def header(self):
        if self._cover_page:
            return
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*self._primary)
        self.cell(0, 8, self.branding.company_name, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, "Domain Health & Security Report", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self._primary)
        self.set_line_width(0.6)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        if self._cover_page:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, self.branding.footer_text, align="C")
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="R")

    # -- helpers -----------------------------------------------------------

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self._primary)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*self._accent)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def sub_title(self, title: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self._accent)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def kv_row(self, key: str, value: str):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(80, 80, 80)
        self.cell(55, 5, key, new_x="RIGHT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, value or "N/A", new_x="LMARGIN", new_y="NEXT")

    def bullet(self, text: str, icon: str = "-"):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(50, 50, 50)
        self.cell(6, 5, icon)
        self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")

    def badge(self, text: str, good: bool):
        if good:
            self.set_fill_color(198, 246, 213)
            self.set_text_color(34, 118, 61)
        else:
            self.set_fill_color(254, 215, 215)
            self.set_text_color(197, 48, 48)
        self.set_font("Helvetica", "B", 8)
        self.cell(30, 5, text, fill=True, align="C", new_x="RIGHT")
        self.set_text_color(0, 0, 0)
        self.cell(3, 5, "")

    def _ensure_space(self, needed: float = 30):
        if self.get_y() + needed > self.h - 20:
            self.add_page()


def generate_pdf(report: DomainReport, branding: BrandingConfig, prepared_by: dict | None = None) -> bytes:
    """Generate a professional PDF report using fpdf2."""
    pdf = _ReportPDF(branding)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    sa = report.security_assessment
    site_name = report.http.site_title or report.domain
    ts = report.timestamp.strftime("%B %d, %Y") if hasattr(report.timestamp, "strftime") else str(report.timestamp)[:10]

    # -- Cover page ---------------------------------------------------------
    pdf._cover_page = True
    pdf.add_page()

    # Top color band
    pdf.set_fill_color(*pdf._primary)
    pdf.rect(0, 0, 210, 100, "F")

    # Company name
    pdf.set_y(25)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, branding.company_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Subtitle
    pdf.set_font("Helvetica", "", 12)
    r, g, b = pdf._accent
    pdf.set_text_color(min(r + 100, 255), min(g + 100, 255), min(b + 100, 255))
    pdf.cell(0, 8, "Domain Health & Security Assessment", align="C", new_x="LMARGIN", new_y="NEXT")

    # Domain / business name block
    pdf.set_y(120)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*pdf._primary)
    pdf.multi_cell(0, 12, site_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    if site_name != report.domain:
        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, report.domain, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Date
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, ts, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)

    # Description
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    desc = (
        "This report provides a comprehensive review of the domain's registration status, "
        "email authentication configuration (SPF, DKIM, DMARC), DNS infrastructure, "
        "website security, and SSL/TLS certificate health. "
        "Findings are scored, explained in plain language, and accompanied by "
        "prioritized recommendations."
    )
    pdf.set_x(25)
    pdf.multi_cell(160, 6, desc, align="C", new_x="LMARGIN", new_y="NEXT")

    # Score preview
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*pdf._primary)
    score = sa.overall_score
    level = sa.risk_level
    pdf.cell(0, 10, f"Overall Score: {score} / 100  --  {level}", align="C", new_x="LMARGIN", new_y="NEXT")

    # Prepared By block
    if prepared_by is not None:
        pdf.ln(10)
        pdf.sub_title("Prepared By")
        pdf.kv_row("Name", prepared_by["name"])
        if prepared_by.get("title"):
            pdf.kv_row("Title", prepared_by["title"])
        if prepared_by.get("phone"):
            pdf.kv_row("Phone", prepared_by["phone"])
        pdf.kv_row("Email", prepared_by["email"])

    # Footer line
    pdf.set_y(270)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 5, branding.footer_text, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf._cover_page = False

    # -- Free-domain advisory page ------------------------------------------
    if report.is_free_domain:
        pdf.add_page()
        pdf.section_title("Advisory: Free Email Domain Detected")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 6,
            f"The email address(es) associated with this report use {report.domain}, "
            "a free consumer email service. While free email works for personal use, "
            "it presents significant drawbacks for business communication.",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(4)

        if report.source_emails:
            pdf.sub_title("Email Addresses Using This Domain")
            for em in report.source_emails:
                pdf.bullet(em)
            pdf.ln(4)

        pdf.sub_title("Why a Business Email Domain Matters")
        benefits = [
            ("Professional credibility", "Emails from yourname@yourcompany.com inspire more trust than a free account. Clients and prospects take you more seriously."),
            ("Brand consistency", "Every email you send reinforces your brand. A custom domain keeps your company name in front of customers."),
            ("Security and control", "With your own domain, you control who has email accounts, can enforce password policies, enable multi-factor authentication, and revoke access when staff leave."),
            ("Email deliverability", "Free domains are more likely to be flagged by spam filters. Business domains with proper SPF, DKIM, and DMARC records have significantly better inbox placement."),
            ("Data ownership", "If an employee leaves and was using a personal Gmail, you lose access to all business correspondence. A company domain means you retain control of business data."),
            ("Compliance readiness", "Many industry regulations and client contracts require business-grade email with audit trails, retention policies, and encryption -- none of which free email provides."),
            ("Scalability", "Platforms like Microsoft 365 and Google Workspace offer shared calendars, file storage, video conferencing, and collaboration tools that free accounts lack."),
        ]
        for title, desc in benefits:
            pdf._ensure_space(20)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*pdf._primary)
            pdf.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, desc, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        pdf.ln(4)
        pdf.sub_title("Recommended Next Steps")
        pdf.bullet("Register a domain that matches your business name (if you haven't already).", "1.")
        pdf.bullet("Set up a business email plan (Microsoft 365 or Google Workspace are popular options).", "2.")
        pdf.bullet("Configure SPF, DKIM, and DMARC records to protect your brand from spoofing.", "3.")
        pdf.bullet("Migrate existing business correspondence to the new domain.", "4.")

    # -- 1. Executive Summary -----------------------------------------------
    pdf.add_page()
    pdf.section_title("1. Executive Summary")

    # Score display
    pdf.set_font("Helvetica", "B", 28)
    score = sa.overall_score
    if score >= 70:
        pdf.set_text_color(34, 118, 61)
    elif score >= 40:
        pdf.set_text_color(180, 130, 30)
    else:
        pdf.set_text_color(197, 48, 48)
    pdf.cell(25, 14, str(score), new_x="RIGHT")

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(15, 14, f"/ 100", new_x="RIGHT")

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 14, f"  {sa.risk_level} Health", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, f"Domain: {report.domain}", new_x="LMARGIN", new_y="NEXT")
    ts = report.timestamp.strftime("%B %d, %Y at %H:%M UTC") if hasattr(report.timestamp, "strftime") else str(report.timestamp)
    pdf.cell(0, 5, f"Report Date: {ts}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Scan ID: {report.scan_id[:8]}...", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Category scores
    pdf.sub_title("Category Scores")
    for cat, val in sa.category_scores.items():
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(55, 5, cat, new_x="RIGHT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 5, str(val), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Key findings
    if sa.weaknesses:
        pdf.sub_title("Key Findings")
        for w in sa.weaknesses[:5]:
            pdf.bullet(w, "!")
        pdf.ln(2)

    # -- Implications -------------------------------------------------------
    if sa.implications:
        pdf.add_page()
        pdf.section_title("What This Means")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, "A plain-language summary of each finding and its business impact.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        _severity_colors = {
            "good": (34, 118, 61),
            "info": (43, 108, 176),
            "warning": (180, 130, 30),
            "critical": (197, 48, 48),
        }
        _severity_labels = {
            "good": "No action needed",
            "info": "For your awareness",
            "warning": "Recommended fix",
            "critical": "Action required",
        }
        for imp in sa.implications:
            pdf._ensure_space(30)
            color = _severity_colors.get(imp.severity, (80, 80, 80))
            label = _severity_labels.get(imp.severity, "")

            # Finding header with severity badge
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*color)
            pdf.cell(0, 5, f"[{label.upper()}]  {imp.finding}", new_x="LMARGIN", new_y="NEXT")

            # Implication body
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 4.5, imp.implication, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        pdf.set_text_color(0, 0, 0)

    # -- 2. Registration Details -------------------------------------------
    pdf.add_page()
    pdf.section_title("2. Registration Details")
    w = report.whois
    pdf.kv_row("Registrar", w.registrar or "N/A")
    pdf.kv_row("Creation Date", str(w.creation_date)[:10] if w.creation_date else "N/A")
    pdf.kv_row("Expiration Date", str(w.expiration_date)[:10] if w.expiration_date else "N/A")
    pdf.kv_row("Updated Date", str(w.updated_date)[:10] if w.updated_date else "N/A")
    pdf.kv_row("Name Servers", ", ".join(w.name_servers) if w.name_servers else "N/A")
    pdf.kv_row("Registrant", w.registrant or "N/A")
    pdf.kv_row("Privacy Protection", "Enabled" if w.privacy_protected else "Not Detected")
    pdf.ln(4)

    # -- 3. Email Configuration --------------------------------------------
    pdf.section_title("3. Email Configuration")

    # MX
    pdf.sub_title("MX Records")
    if report.email_security.mx_records:
        for mx in report.email_security.mx_records:
            pdf.bullet(mx)
    else:
        pdf.bullet("No MX records found", "!")
    pdf.ln(2)

    # SPF
    pdf.sub_title("SPF (Sender Policy Framework)")
    spf = report.email_security.spf
    pdf.set_font("Helvetica", "", 9)
    pdf.badge("Valid" if spf.valid else ("Missing" if not spf.record else "Issues"), spf.valid)
    pdf.ln(5)
    if spf.record:
        pdf.kv_row("Record", spf.record)
    for issue in spf.issues:
        pdf.bullet(issue, "!")
    pdf.ln(2)

    # DMARC
    pdf._ensure_space(40)
    pdf.sub_title("DMARC")
    dmarc = report.email_security.dmarc
    pdf.badge(
        dmarc.policy.title() if dmarc.policy else ("Missing" if not dmarc.record else "Invalid"),
        dmarc.valid and dmarc.policy in ("reject", "quarantine"),
    )
    pdf.ln(5)
    if dmarc.record:
        pdf.kv_row("Record", dmarc.record)
    pdf.kv_row("Policy", dmarc.policy or "N/A")
    for issue in dmarc.issues:
        pdf.bullet(issue, "!")
    pdf.ln(2)

    # DKIM
    pdf._ensure_space(30)
    pdf.sub_title("DKIM")
    dkim = report.email_security.dkim
    pdf.badge("Found" if dkim.found else "Not Detected", dkim.found)
    pdf.ln(5)
    if dkim.selectors_found:
        pdf.kv_row("Selectors Found", ", ".join(dkim.selectors_found))
    else:
        pdf.kv_row("Selectors Checked", str(len(dkim.selectors_checked)))
        pdf.bullet("No DKIM selectors detected among common names.", "!")
    pdf.ln(4)

    # -- 4. DNS & Infrastructure -------------------------------------------
    pdf.add_page()
    pdf.section_title("4. DNS & Infrastructure")

    dns_d = report.dns
    if dns_d.a_records:
        pdf.kv_row("A Records", ", ".join(dns_d.a_records))
    if dns_d.aaaa_records:
        pdf.kv_row("AAAA Records", ", ".join(dns_d.aaaa_records))
    pdf.kv_row("Name Servers", ", ".join(dns_d.ns_records) if dns_d.ns_records else "N/A")

    pdf.ln(2)
    pdf.sub_title("DNSSEC")
    pdf.badge("Enabled" if report.dnssec.enabled else "Not Enabled", report.dnssec.enabled)
    pdf.ln(5)
    pdf.kv_row("Details", report.dnssec.details)
    pdf.ln(4)

    # -- 5. Web & Certificate ----------------------------------------------
    pdf.section_title("5. Web & Certificate")

    h = report.http
    pdf.sub_title("HTTP Connectivity")
    pdf.kv_row("Reachable", "Yes" if h.reachable else "No")
    pdf.kv_row("HTTPS Enabled", "Yes" if h.https_enabled else "No")
    pdf.kv_row("HTTP->HTTPS Redirect", "Yes" if h.redirect_to_https else "No")
    pdf.kv_row("Status Code", str(h.status_code) if h.status_code else "N/A")
    if h.response_time_ms is not None:
        pdf.kv_row("Response Time", f"{h.response_time_ms:.0f} ms")
    pdf.ln(2)

    ssl_d = report.ssl
    pdf._ensure_space(50)
    pdf.sub_title("SSL/TLS Certificate")
    pdf.badge("Valid" if ssl_d.valid else "Invalid", ssl_d.valid)
    pdf.ln(5)
    pdf.kv_row("Issuer", ssl_d.issuer or "N/A")
    pdf.kv_row("Subject", ssl_d.subject or "N/A")
    pdf.kv_row("Valid From", str(ssl_d.not_before)[:10] if ssl_d.not_before else "N/A")
    pdf.kv_row("Valid Until", str(ssl_d.not_after)[:10] if ssl_d.not_after else "N/A")
    if ssl_d.days_until_expiry is not None:
        pdf.kv_row("Days Until Expiry", str(ssl_d.days_until_expiry))
    for issue in ssl_d.issues:
        pdf.bullet(issue, "!")
    pdf.ln(4)

    # -- 6. Security Assessment & Recommendations --------------------------
    pdf.add_page()
    pdf.section_title("6. Security Assessment & Recommendations")

    if sa.strengths:
        pdf.sub_title("Strengths")
        for s in sa.strengths:
            pdf.set_text_color(34, 118, 61)
            pdf.bullet(s, "+")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    if sa.weaknesses:
        pdf._ensure_space(30)
        pdf.sub_title("Areas for Improvement")
        for w_item in sa.weaknesses:
            pdf.set_text_color(197, 48, 48)
            pdf.bullet(w_item, "!")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    if sa.recommendations:
        pdf._ensure_space(30)
        pdf.sub_title("Recommended Actions")
        for i, rec in enumerate(sa.recommendations, 1):
            pdf.set_text_color(50, 50, 50)
            pdf.bullet(rec, f"{i}.")
        pdf.ln(4)

    return pdf.output()
