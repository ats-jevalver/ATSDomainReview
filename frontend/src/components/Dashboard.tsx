import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { BarChart3, AlertTriangle, CheckCircle2 } from "lucide-react";
import DomainInput from "./DomainInput";
import DomainCard from "./DomainCard";
import { getScanResults } from "../api";
import type { DomainReport } from "../types";

export default function Dashboard() {
  const [searchParams] = useSearchParams();
  const scanId = searchParams.get("scan");
  const [results, setResults] = useState<DomainReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;
    setLoading(true);
    getScanResults(scanId)
      .then(setResults)
      .catch(() => setError("Failed to load results."))
      .finally(() => setLoading(false));
  }, [scanId]);

  const avgScore =
    results.length > 0
      ? Math.round(
          results.reduce(
            (sum, r) => sum + r.security_assessment.overall_score,
            0
          ) / results.length
        )
      : 0;

  const needsAttention = results.filter(
    (r) => r.security_assessment.risk_level === "Poor"
  ).length;

  return (
    <div className="space-y-8">
      <DomainInput />

      {loading && (
        <div className="flex justify-center py-12">
          <svg
            className="animate-spin w-8 h-8 text-accent"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 text-danger rounded-lg text-sm">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard
              icon={<BarChart3 className="w-5 h-5 text-accent" />}
              label="Total Domains"
              value={String(results.length)}
            />
            <StatCard
              icon={<CheckCircle2 className="w-5 h-5 text-success" />}
              label="Average Score"
              value={`${avgScore}/100`}
            />
            <StatCard
              icon={<AlertTriangle className="w-5 h-5 text-warning" />}
              label="Needs Attention"
              value={String(needsAttention)}
            />
          </div>

          <div>
            <h2 className="text-lg font-semibold text-primary mb-4">
              Domain Results
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {results.map((r) => (
                <DomainCard key={r.domain} report={r} />
              ))}
            </div>
          </div>
        </>
      )}

      {!loading && !error && results.length === 0 && !scanId && (
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p className="text-sm">
            Add domains above and start a scan to see results here.
          </p>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center gap-4">
      <div className="p-2.5 bg-gray-50 rounded-lg">{icon}</div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">
          {label}
        </p>
        <p className="text-xl font-bold text-primary">{value}</p>
      </div>
    </div>
  );
}
