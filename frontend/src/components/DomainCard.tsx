import { useNavigate } from "react-router-dom";
import {
  Mail,
  ShieldCheck,
  Globe,
  FileDown,
  ArrowRight,
} from "lucide-react";
import ScoreBadge from "./ScoreBadge";
import { downloadPdf } from "../api";
import type { DomainReport } from "../types";

interface DomainCardProps {
  report: DomainReport;
}

function statusIcon(ok: boolean | null | undefined) {
  if (ok === true)
    return <span className="text-success text-xs font-bold">OK</span>;
  if (ok === false)
    return <span className="text-danger text-xs font-bold">!</span>;
  return <span className="text-gray-400 text-xs">--</span>;
}

function topFindings(report: DomainReport): string[] {
  const a = report.security_assessment;
  const items: string[] = [];

  if (a.weaknesses.length > 0) {
    items.push(...a.weaknesses.slice(0, 2));
  }
  if (items.length === 0 && a.strengths.length > 0) {
    items.push(...a.strengths.slice(0, 2));
  }
  if (a.recommendations.length > 0 && items.length < 3) {
    items.push(a.recommendations[0]!);
  }
  return items.slice(0, 3);
}

export default function DomainCard({ report }: DomainCardProps) {
  const navigate = useNavigate();
  const score = report.security_assessment.overall_score;
  const risk = report.security_assessment.risk_level;

  const emailOk =
    report.email_security.spf.valid && report.email_security.dmarc.valid;
  const sslOk = report.ssl.valid;
  const dnsOk = report.dns.a_records.length > 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex flex-col gap-4 animate-fade-in hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-primary">
            {report.domain}
          </h3>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-xs text-gray-500">
              Scanned {new Date(report.timestamp).toLocaleDateString()}
            </p>
            {report.is_free_domain && (
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-800">
                Free Email
              </span>
            )}
          </div>
        </div>
        <ScoreBadge score={score} riskLevel={risk} size="sm" />
      </div>

      {/* Quick stats */}
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <span className="flex items-center gap-1" title="Email Security">
          <Mail className="w-4 h-4 text-gray-400" />
          {statusIcon(emailOk)}
        </span>
        <span className="flex items-center gap-1" title="SSL/TLS">
          <ShieldCheck className="w-4 h-4 text-gray-400" />
          {statusIcon(sslOk)}
        </span>
        <span className="flex items-center gap-1" title="DNS">
          <Globe className="w-4 h-4 text-gray-400" />
          {statusIcon(dnsOk)}
        </span>
      </div>

      {/* Findings */}
      <ul className="text-sm text-gray-600 space-y-1">
        {topFindings(report).map((f, i) => (
          <li key={i} className="flex items-start gap-1.5">
            <span className="mt-1 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
            <span className="line-clamp-1">{f}</span>
          </li>
        ))}
      </ul>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-auto pt-2 border-t border-gray-100">
        <button
          onClick={() =>
            navigate(
              `/scan/${report.scan_id}/report/${encodeURIComponent(report.domain)}`
            )
          }
          className="flex-1 inline-flex items-center justify-center gap-1 px-3 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-primary-light transition-colors"
        >
          View Report
          <ArrowRight className="w-4 h-4" />
        </button>
        <button
          onClick={() => downloadPdf(report.scan_id, report.domain)}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-primary border border-primary rounded-lg hover:bg-primary hover:text-white transition-colors"
          title="Download PDF"
        >
          <FileDown className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
