import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, X, Upload, Trash2, Send, List, Type, Mail } from "lucide-react";
import { submitDomains, submitEmails, uploadCsv } from "../api";

type Tab = "manual" | "paste" | "csv" | "emails";

const DOMAIN_REGEX = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidDomain(d: string): boolean {
  return DOMAIN_REGEX.test(d.trim());
}

export default function DomainInput() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("manual");
  const [domains, setDomains] = useState<string[]>([]);
  const [manualValue, setManualValue] = useState("");
  const [pasteValue, setPasteValue] = useState("");
  const [emailPasteValue, setEmailPasteValue] = useState("");
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  const addDomain = useCallback(() => {
    const d = manualValue.trim().toLowerCase();
    if (!d) return;
    if (!isValidDomain(d)) {
      setManualError("Invalid domain format");
      return;
    }
    if (domains.includes(d)) {
      setManualError("Domain already added");
      return;
    }
    setDomains((prev) => [...prev, d]);
    setManualValue("");
    setManualError(null);
  }, [manualValue, domains]);

  const removeDomain = (d: string) => {
    setDomains((prev) => prev.filter((x) => x !== d));
  };

  const handlePasteAdd = () => {
    const lines = pasteValue
      .split(/[\n,;]+/)
      .map((l) => l.trim().toLowerCase())
      .filter(Boolean);
    const valid: string[] = [];
    const invalid: string[] = [];
    for (const l of lines) {
      if (isValidDomain(l)) {
        if (!domains.includes(l) && !valid.includes(l)) valid.push(l);
      } else {
        invalid.push(l);
      }
    }
    setDomains((prev) => [...prev, ...valid]);
    setPasteValue("");
    if (invalid.length > 0) {
      setError(`Skipped invalid entries: ${invalid.join(", ")}`);
    } else {
      setError(null);
    }
  };

  const handleCsvUpload = async () => {
    if (!csvFile) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await uploadCsv(csvFile);
      navigate(`/scan/${res.scan_id}`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEmailSubmit = async () => {
    const lines = emailPasteValue
      .split(/[\n,;]+/)
      .map((l) => l.trim().toLowerCase())
      .filter(Boolean);
    const valid: string[] = [];
    const invalid: string[] = [];
    for (const l of lines) {
      if (EMAIL_REGEX.test(l)) {
        if (!valid.includes(l)) valid.push(l);
      } else {
        invalid.push(l);
      }
    }
    if (invalid.length > 0) {
      setError(`Skipped invalid email(s): ${invalid.join(", ")}`);
    }
    if (valid.length === 0) {
      setError("No valid email addresses found.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const res = await submitEmails(valid);
      navigate(`/scan/${res.scan_id}`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Submission failed. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    if (tab === "csv") {
      await handleCsvUpload();
      return;
    }
    if (tab === "emails") {
      await handleEmailSubmit();
      return;
    }
    if (domains.length === 0) {
      setError("Add at least one domain before scanning.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitDomains(domains);
      navigate(`/scan/${res.scan_id}`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Submission failed. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "manual", label: "Manual Entry", icon: <Type className="w-4 h-4" /> },
    { key: "paste", label: "Paste Domains", icon: <List className="w-4 h-4" /> },
    { key: "emails", label: "Email Addresses", icon: <Mail className="w-4 h-4" /> },
    { key: "csv", label: "CSV Upload", icon: <Upload className="w-4 h-4" /> },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-fade-in">
      <h2 className="text-lg font-semibold text-primary mb-4">
        Add Domains to Scan
      </h2>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-4 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => {
              setTab(t.key);
              setError(null);
            }}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px whitespace-nowrap ${
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Manual entry */}
      {tab === "manual" && (
        <div>
          <div className="flex gap-2">
            <div className="flex-1">
              <input
                type="text"
                value={manualValue}
                onChange={(e) => {
                  setManualValue(e.target.value);
                  setManualError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addDomain();
                  }
                }}
                placeholder="example.com"
                className={`w-full px-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 ${
                  manualError
                    ? "border-danger focus:ring-danger/40"
                    : "border-gray-300"
                }`}
              />
              {manualError && (
                <p className="mt-1 text-xs text-danger">{manualError}</p>
              )}
            </div>
            <button
              onClick={addDomain}
              className="inline-flex items-center gap-1 px-4 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-primary-light transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add
            </button>
          </div>
        </div>
      )}

      {/* Paste domains */}
      {tab === "paste" && (
        <div>
          <textarea
            value={pasteValue}
            onChange={(e) => setPasteValue(e.target.value)}
            rows={5}
            placeholder={"example.com\nanother-domain.org\nthird.net"}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 resize-y"
          />
          <button
            onClick={handlePasteAdd}
            disabled={!pasteValue.trim()}
            className="mt-2 inline-flex items-center gap-1 px-4 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus className="w-4 h-4" />
            Add Domains
          </button>
        </div>
      )}

      {/* Email addresses */}
      {tab === "emails" && (
        <div>
          <p className="text-sm text-gray-500 mb-2">
            Paste email addresses below. Domains will be extracted automatically.
            Free email providers (Gmail, Outlook, etc.) will include a business email advisory.
          </p>
          <textarea
            value={emailPasteValue}
            onChange={(e) => setEmailPasteValue(e.target.value)}
            rows={5}
            placeholder={"john@acme.com\njane@gmail.com\nmike@initech.net"}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 resize-y font-mono"
          />
          {emailPasteValue.trim() && (
            <p className="mt-1 text-xs text-gray-400">
              {emailPasteValue.split(/[\n,;]+/).filter((l) => EMAIL_REGEX.test(l.trim())).length} valid email(s) detected
            </p>
          )}
        </div>
      )}

      {/* CSV upload */}
      {tab === "csv" && (
        <div>
          <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-accent transition-colors">
            <Upload className="w-8 h-8 text-gray-400 mb-2" />
            <span className="text-sm text-gray-500">
              {csvFile ? csvFile.name : "Click or drag a CSV file"}
            </span>
            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setCsvFile(f);
              }}
            />
          </label>
        </div>
      )}

      {/* Domain chips (shown for manual + paste tabs) */}
      {(tab === "manual" || tab === "paste") && domains.length > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              {domains.length} domain{domains.length !== 1 ? "s" : ""} added
            </span>
            <button
              onClick={() => setDomains([])}
              className="text-xs text-danger hover:underline flex items-center gap-1"
            >
              <Trash2 className="w-3 h-3" />
              Clear all
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {domains.map((d) => (
              <span
                key={d}
                className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-primary text-sm rounded-full"
              >
                {d}
                <button
                  onClick={() => removeDomain(d)}
                  className="text-primary/60 hover:text-danger transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 text-danger text-sm rounded-lg">
          {error}
        </div>
      )}

      {/* Submit */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={
            submitting ||
            (tab === "csv"
              ? !csvFile
              : tab === "emails"
                ? !emailPasteValue.trim()
                : domains.length === 0)
          }
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary text-white font-medium rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <>
              <svg
                className="animate-spin w-4 h-4"
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
              Submitting...
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              Start Scan
            </>
          )}
        </button>
      </div>
    </div>
  );
}
