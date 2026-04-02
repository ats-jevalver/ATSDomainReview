import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Mail,
  Globe,
  ShieldCheck,
  Server,
  Lock,
  Info,
  FileText,
} from "lucide-react";
import ScoreBadge from "./ScoreBadge";
import ExportButtons from "./ExportButtons";
import { getScanResults } from "../api";
import type { DomainReport, Implication } from "../types";

export default function ReportView() {
  const { scanId, domain } = useParams<{ scanId: string; domain: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<DomainReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId || !domain) return;
    setLoading(true);
    getScanResults(scanId)
      .then((results) => {
        const match = results.find(
          (r) => r.domain === decodeURIComponent(domain)
        );
        if (match) {
          setReport(match);
        } else {
          setError("Domain not found in scan results.");
        }
      })
      .catch(() => setError("Failed to load report."))
      .finally(() => setLoading(false));
  }, [scanId, domain]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="text-center py-16">
        <XCircle className="w-12 h-12 text-danger mx-auto mb-4" />
        <p className="text-gray-700 mb-4">{error ?? "Report not available."}</p>
        <button
          onClick={() => navigate(-1)}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
        >
          Go Back
        </button>
      </div>
    );
  }

  const a = report.security_assessment;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top bar */}
      <div className="flex items-center justify-between no-print">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        {scanId && (
          <ExportButtons scanId={scanId} domain={report.domain} />
        )}
      </div>

      {/* Free domain advisory */}
      {report.is_free_domain && (
        <section className="bg-yellow-50 rounded-xl shadow-sm border border-yellow-200 p-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-yellow-800 mb-3">
            <AlertTriangle className="w-5 h-5" />
            Advisory: Free Email Domain Detected
          </h2>
          <p className="text-sm text-gray-700 mb-3">
            The email address(es) associated with this report use <strong>{report.domain}</strong>,
            a free consumer email service. While free email works for personal use,
            it presents significant drawbacks for business communication.
          </p>
          {report.source_emails.length > 0 && (
            <p className="text-xs text-gray-500 mb-4">
              <strong>Addresses:</strong> {report.source_emails.join(", ")}
            </p>
          )}
          <h3 className="text-sm font-semibold text-gray-800 mb-2">Why a Business Email Domain Matters</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            {[
              ["Professional credibility", "Emails from yourname@yourcompany.com inspire more trust than a free account."],
              ["Brand consistency", "Every email reinforces your brand and keeps your company name in front of customers."],
              ["Security & control", "Enforce password policies, enable MFA, and revoke access when staff leave."],
              ["Email deliverability", "Business domains with SPF, DKIM, and DMARC have significantly better inbox placement."],
              ["Data ownership", "Company domain means you retain control of business correspondence."],
              ["Compliance readiness", "Many regulations require audit trails and encryption that free email lacks."],
            ].map(([title, desc]) => (
              <div key={title} className="p-2 bg-white rounded border border-yellow-100">
                <div className="font-medium text-gray-800">{title}</div>
                <div className="text-gray-600 text-xs mt-0.5">{desc}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Executive summary */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-primary">
              {report.domain}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Scanned on{" "}
              {new Date(report.timestamp).toLocaleString()}
            </p>
          </div>
          <ScoreBadge
            score={a.overall_score}
            riskLevel={a.risk_level}
            size="lg"
          />
        </div>

        {/* Category scores */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-5 gap-3">
          {Object.entries(a.category_scores).map(([label, score]) => (
            <CategoryScore key={label} label={label} score={score} />
          ))}
        </div>
      </section>

      {/* Implications */}
      {a.implications && a.implications.length > 0 && (
        <Section
          title="What This Means"
          icon={<FileText className="w-5 h-5" />}
        >
          <p className="text-sm text-gray-500 mb-4">
            A plain-language summary of each finding and its business impact.
          </p>
          <div className="space-y-3">
            {a.implications.map((imp, i) => (
              <ImplicationCard key={i} implication={imp} />
            ))}
          </div>
        </Section>
      )}

      {/* Registration Details */}
      <Section
        title="Registration Details"
        icon={<Globe className="w-5 h-5" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
          <DetailRow label="Registrar" value={report.whois.registrar} />
          <DetailRow label="Registrant" value={report.whois.registrant} />
          <DetailRow
            label="Creation Date"
            value={report.whois.creation_date ? new Date(report.whois.creation_date).toLocaleDateString() : null}
          />
          <DetailRow
            label="Expiration Date"
            value={report.whois.expiration_date ? new Date(report.whois.expiration_date).toLocaleDateString() : null}
          />
          <DetailRow
            label="Updated Date"
            value={report.whois.updated_date ? new Date(report.whois.updated_date).toLocaleDateString() : null}
          />
          <DetailRow
            label="Privacy Protection"
            value={report.whois.privacy_protected ? "Enabled" : "Not Detected"}
          />
          <DetailRow
            label="Name Servers"
            value={report.whois.name_servers.join(", ") || null}
          />
        </div>
      </Section>

      {/* Email Configuration */}
      <Section
        title="Email Configuration"
        icon={<Mail className="w-5 h-5" />}
      >
        <div className="space-y-4">
          {/* MX Records */}
          {report.email_security.mx_records.length > 0 && (
            <div className="text-sm">
              <p className="font-medium text-gray-700 mb-1">MX Records</p>
              <div className="space-y-0.5">
                {report.email_security.mx_records.map((mx, i) => (
                  <p key={i} className="font-mono text-xs text-gray-600">{mx}</p>
                ))}
              </div>
            </div>
          )}

          {/* SPF */}
          <SubSection
            title="SPF (Sender Policy Framework)"
            valid={report.email_security.spf.valid}
          >
            <div className="text-sm space-y-1">
              <DetailRow
                label="Record"
                value={report.email_security.spf.record}
                mono
              />
              <Issues items={report.email_security.spf.issues} />
            </div>
          </SubSection>

          {/* DMARC */}
          <SubSection
            title="DMARC"
            valid={report.email_security.dmarc.valid}
          >
            <div className="text-sm space-y-1">
              <DetailRow
                label="Record"
                value={report.email_security.dmarc.record}
                mono
              />
              <DetailRow
                label="Policy"
                value={report.email_security.dmarc.policy}
              />
              <Issues items={report.email_security.dmarc.issues} />
            </div>
          </SubSection>

          {/* DKIM */}
          <SubSection
            title="DKIM"
            valid={report.email_security.dkim.found}
          >
            <div className="text-sm space-y-1">
              <DetailRow
                label="Selectors Found"
                value={
                  report.email_security.dkim.selectors_found.length > 0
                    ? report.email_security.dkim.selectors_found.join(", ")
                    : `None of ${report.email_security.dkim.selectors_checked.length} common selectors detected`
                }
              />
            </div>
          </SubSection>
        </div>
      </Section>

      {/* DNS / Infrastructure */}
      <Section
        title="DNS & Infrastructure"
        icon={<Server className="w-5 h-5" />}
      >
        <div className="text-sm space-y-2">
          <DetailRow
            label="A Records"
            value={report.dns.a_records.join(", ") || null}
            mono
          />
          <DetailRow
            label="AAAA Records"
            value={report.dns.aaaa_records.join(", ") || null}
            mono
          />
          <DetailRow
            label="MX Records"
            value={report.dns.mx_records.join(", ") || null}
            mono
          />
          <DetailRow
            label="NS Records"
            value={report.dns.ns_records.join(", ") || null}
            mono
          />

          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="font-medium text-gray-700 mb-1">DNSSEC</p>
            <DetailRow
              label="Enabled"
              value={report.dnssec.enabled ? "Yes" : "No"}
            />
            <DetailRow label="Details" value={report.dnssec.details} />
          </div>
        </div>
      </Section>

      {/* Web / Certificate */}
      <Section
        title="Web & Certificate"
        icon={<Lock className="w-5 h-5" />}
      >
        <div className="space-y-4">
          {/* HTTP */}
          <div className="text-sm space-y-1">
            <p className="font-medium text-gray-700 mb-1">HTTP Connectivity</p>
            <DetailRow
              label="Reachable"
              value={report.http.reachable ? "Yes" : "No"}
            />
            <DetailRow
              label="HTTPS Enabled"
              value={report.http.https_enabled ? "Yes" : "No"}
            />
            <DetailRow
              label="HTTP to HTTPS Redirect"
              value={report.http.redirect_to_https ? "Yes" : "No"}
            />
            <DetailRow
              label="Status Code"
              value={
                report.http.status_code != null
                  ? String(report.http.status_code)
                  : null
              }
            />
            <DetailRow
              label="Response Time"
              value={
                report.http.response_time_ms != null
                  ? `${Math.round(report.http.response_time_ms)} ms`
                  : null
              }
            />
          </div>

          {/* SSL */}
          <div className="text-sm space-y-1 pt-3 border-t border-gray-100">
            <p className="font-medium text-gray-700 mb-1">SSL/TLS Certificate</p>
            <DetailRow
              label="Valid"
              value={report.ssl.valid ? "Yes" : "No"}
            />
            <DetailRow label="Issuer" value={report.ssl.issuer} />
            <DetailRow label="Subject" value={report.ssl.subject} />
            <DetailRow
              label="Valid From"
              value={report.ssl.not_before ? new Date(report.ssl.not_before).toLocaleDateString() : null}
            />
            <DetailRow
              label="Valid Until"
              value={report.ssl.not_after ? new Date(report.ssl.not_after).toLocaleDateString() : null}
            />
            <DetailRow
              label="Days Until Expiry"
              value={
                report.ssl.days_until_expiry != null
                  ? String(report.ssl.days_until_expiry)
                  : null
              }
            />
            <Issues items={report.ssl.issues} />
          </div>
        </div>
      </Section>

      {/* Security Assessment */}
      <Section
        title="Security Assessment"
        icon={<ShieldCheck className="w-5 h-5" />}
      >
        <div className="space-y-4">
          {a.strengths.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-success mb-2">
                Strengths
              </h4>
              <ul className="space-y-1">
                {a.strengths.map((s, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-gray-700"
                  >
                    <CheckCircle2 className="w-4 h-4 text-success shrink-0 mt-0.5" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {a.weaknesses.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-danger mb-2">
                Weaknesses
              </h4>
              <ul className="space-y-1">
                {a.weaknesses.map((w, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-gray-700"
                  >
                    <XCircle className="w-4 h-4 text-danger shrink-0 mt-0.5" />
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {a.recommendations.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-warning mb-2">
                Recommendations
              </h4>
              <ul className="space-y-1">
                {a.recommendations.map((rec, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-gray-700"
                  >
                    <AlertTriangle className="w-4 h-4 text-warning shrink-0 mt-0.5" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </Section>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Helper components                                                   */
/* ------------------------------------------------------------------ */

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 print-break-before">
      <h2 className="flex items-center gap-2 text-lg font-semibold text-primary mb-4">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

function SubSection({
  title,
  valid,
  children,
}: {
  title: string;
  valid: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        {valid ? (
          <CheckCircle2 className="w-4 h-4 text-success" />
        ) : (
          <XCircle className="w-4 h-4 text-danger" />
        )}
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-x-2 py-0.5">
      <span className="text-gray-500 min-w-[160px]">{label}:</span>
      <span
        className={`text-gray-800 break-all ${mono ? "font-mono text-xs" : ""}`}
      >
        {value ?? <span className="text-gray-400 italic">N/A</span>}
      </span>
    </div>
  );
}

function Issues({ items }: { items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-1 space-y-0.5">
      {items.map((w, i) => (
        <p key={i} className="text-xs text-warning flex items-center gap-1">
          <AlertTriangle className="w-3 h-3 shrink-0" />
          {w}
        </p>
      ))}
    </div>
  );
}

function ImplicationCard({ implication }: { implication: Implication }) {
  const styles: Record<string, { border: string; bg: string; icon: React.ReactNode; label: string }> = {
    good: {
      border: "border-green-200",
      bg: "bg-green-50",
      icon: <CheckCircle2 className="w-5 h-5 text-success shrink-0 mt-0.5" />,
      label: "No action needed",
    },
    info: {
      border: "border-blue-200",
      bg: "bg-blue-50",
      icon: <Info className="w-5 h-5 text-accent shrink-0 mt-0.5" />,
      label: "For your awareness",
    },
    warning: {
      border: "border-yellow-200",
      bg: "bg-yellow-50",
      icon: <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />,
      label: "Recommended fix",
    },
    critical: {
      border: "border-red-200",
      bg: "bg-red-50",
      icon: <XCircle className="w-5 h-5 text-danger shrink-0 mt-0.5" />,
      label: "Action required",
    },
  };
  const s = styles[implication.severity] ?? styles.info!;

  return (
    <div className={`rounded-lg border ${s.border} ${s.bg} p-4`}>
      <div className="flex items-start gap-3">
        {s.icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold text-gray-800">
              {implication.finding}
            </h4>
            <span className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${
              implication.severity === "good" ? "bg-green-200 text-green-800" :
              implication.severity === "warning" ? "bg-yellow-200 text-yellow-800" :
              implication.severity === "critical" ? "bg-red-200 text-red-800" :
              "bg-blue-200 text-blue-800"
            }`}>
              {s.label}
            </span>
          </div>
          <p className="text-sm text-gray-600 mt-1 leading-relaxed">
            {implication.implication}
          </p>
        </div>
      </div>
    </div>
  );
}

function CategoryScore({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
  const color =
    score >= 12
      ? "bg-green-100 text-green-800"
      : score >= 6
        ? "bg-yellow-100 text-yellow-800"
        : "bg-red-100 text-red-800";

  return (
    <div className="flex flex-col items-center gap-1 p-3 rounded-lg bg-gray-50">
      <span className={`text-lg font-bold px-2 py-0.5 rounded ${color}`}>
        {score}
      </span>
      <span className="text-xs text-gray-500 text-center">{label}</span>
    </div>
  );
}
