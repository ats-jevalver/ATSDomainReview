import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowRight,
} from "lucide-react";
import { getScanStatus, getScanResults } from "../api";
import type { ScanStatus, DomainReport } from "../types";
import DomainCard from "./DomainCard";
import ExportButtons from "./ExportButtons";

export default function ScanProgress() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const [results, setResults] = useState<DomainReport[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isComplete = status?.status === "completed" || status?.status === "failed";

  const fetchStatus = useCallback(async () => {
    if (!scanId) return;
    try {
      const s = await getScanStatus(scanId);
      setStatus(s);

      // If scan is complete and results come embedded in status
      if ((s.status === "completed" || s.status === "failed") && s.results) {
        setResults(s.results);
      } else if (s.status === "completed" || s.status === "failed") {
        const r = await getScanResults(scanId);
        setResults(r);
      }
    } catch {
      setError("Failed to fetch scan status. The server may be unavailable.");
    }
  }, [scanId]);

  useEffect(() => {
    fetchStatus();
    if (isComplete) return;
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [fetchStatus, isComplete]);

  if (error) {
    return (
      <div className="text-center py-16">
        <XCircle className="w-12 h-12 text-danger mx-auto mb-4" />
        <p className="text-gray-700 mb-4">{error}</p>
        <button
          onClick={() => {
            setError(null);
            fetchStatus();
          }}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-light transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
      </div>
    );
  }

  const pct =
    status.total > 0
      ? Math.round((status.completed / status.total) * 100)
      : 0;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Progress header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary">
            Scan Progress
          </h2>
          {isComplete && scanId && (
            <ExportButtons scanId={scanId} />
          )}
        </div>

        {/* Progress bar */}
        <div className="mb-2">
          <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
            <span>
              {status.completed} of {status.total} domains
            </span>
            <span>{pct}%</span>
          </div>
          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isComplete ? "bg-success" : "bg-accent progress-bar-animated"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Status text */}
        <div className="mt-4 flex items-center gap-2 text-sm">
          {isComplete ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-success" />
              <span className="text-gray-700">Scan complete</span>
            </>
          ) : (
            <>
              <Loader2 className="w-4 h-4 text-accent animate-spin" />
              <span className="text-gray-700">Scanning domains...</span>
            </>
          )}
        </div>
      </div>

      {/* Results grid */}
      {isComplete && results && results.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-primary">Results</h2>
            <button
              onClick={() => navigate("/")}
              className="text-sm text-accent hover:underline flex items-center gap-1"
            >
              Back to Dashboard
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {results.map((r) => (
              <DomainCard key={r.domain} report={r} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
