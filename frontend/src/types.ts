/* TypeScript interfaces matching backend Pydantic models exactly. */

export interface WhoisData {
  registrar: string | null;
  creation_date: string | null;
  expiration_date: string | null;
  updated_date: string | null;
  name_servers: string[];
  registrant: string | null;
  privacy_protected: boolean;
}

export interface DnsData {
  a_records: string[];
  aaaa_records: string[];
  cname_records: string[];
  mx_records: string[];
  ns_records: string[];
  txt_records: string[];
}

export interface SpfData {
  record: string | null;
  valid: boolean;
  issues: string[];
}

export interface DmarcData {
  record: string | null;
  policy: string | null;
  valid: boolean;
  issues: string[];
}

export interface DkimData {
  found: boolean;
  selectors_checked: string[];
  selectors_found: string[];
  records: Record<string, string>;
}

export interface DnssecData {
  enabled: boolean;
  details: string;
}

export interface SslData {
  valid: boolean;
  issuer: string | null;
  subject: string | null;
  not_before: string | null;
  not_after: string | null;
  days_until_expiry: number | null;
  issues: string[];
}

export interface HttpData {
  reachable: boolean;
  https_enabled: boolean;
  redirect_to_https: boolean;
  status_code: number | null;
  response_time_ms: number | null;
  site_title: string | null;
}

export interface EmailSecurityData {
  spf: SpfData;
  dmarc: DmarcData;
  dkim: DkimData;
  mx_records: string[];
  overall_email_score: number;
  issues: string[];
  recommendations: string[];
}

export interface Implication {
  finding: string;
  implication: string;
  severity: "good" | "info" | "warning" | "critical";
}

export interface SecurityAssessment {
  overall_score: number;
  risk_level: string; // "Good" | "Moderate" | "Poor"
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  implications: Implication[];
  category_scores: Record<string, number>;
}

export interface DomainReport {
  domain: string;
  scan_id: string;
  timestamp: string;
  is_free_domain: boolean;
  source_emails: string[];
  whois: WhoisData;
  dns: DnsData;
  email_security: EmailSecurityData;
  dnssec: DnssecData;
  ssl: SslData;
  http: HttpData;
  security_assessment: SecurityAssessment;
}

export interface ScanResponse {
  scan_id: string;
  status: string;
  domains: string[];
}

export interface ScanStatus {
  scan_id: string;
  status: "pending" | "running" | "completed" | "failed";
  total: number;
  completed: number;
  results: DomainReport[] | null;
}

export interface BrandingConfig {
  company_name: string;
  logo_url: string;
  primary_color: string;
  accent_color: string;
  footer_text: string;
}

export interface UserProfile {
  oid: string;
  name: string;
  email: string;
  title: string | null;
  phone: string | null;
}
