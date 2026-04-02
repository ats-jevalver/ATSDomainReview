"""Branding and application configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class BrandingSettings:
    """Branding configuration for reports and UI."""

    company_name: str = field(
        default_factory=lambda: os.environ.get("ATS_COMPANY_NAME", "ATS Domain Review")
    )
    logo_url: str = field(
        default_factory=lambda: os.environ.get("ATS_LOGO_URL", "")
    )
    primary_color: str = field(
        default_factory=lambda: os.environ.get("ATS_PRIMARY_COLOR", "#1a365d")
    )
    accent_color: str = field(
        default_factory=lambda: os.environ.get("ATS_ACCENT_COLOR", "#2b6cb0")
    )
    footer_text: str = field(
        default_factory=lambda: os.environ.get(
            "ATS_FOOTER_TEXT",
            "Confidential - Prepared by ATS Domain Review"
        )
    )


# Singleton instance used throughout the application.
branding = BrandingSettings()


@dataclass
class AppSettings:
    """General application settings."""

    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql://ats_user:ats_pass@10.10.10.20:5432/ats_domain_review"
        )
    )
    max_concurrent_scans: int = 5
    collector_timeout: int = 10
    dns_timeout: int = 5
    http_timeout: int = 10
    static_dir: str = field(
        default_factory=lambda: os.environ.get("ATS_STATIC_DIR", "static")
    )


app_settings = AppSettings()


@dataclass
class AzureAdSettings:
    """Azure AD / Entra ID configuration for Microsoft 365 SSO."""

    client_id: str = field(
        default_factory=lambda: os.environ.get("AZURE_CLIENT_ID", "")
    )
    tenant_id: str = field(
        default_factory=lambda: os.environ.get("AZURE_TENANT_ID", "common")
    )
    client_secret: str = field(
        default_factory=lambda: os.environ.get("AZURE_CLIENT_SECRET", "")
    )


azure_ad = AzureAdSettings()
