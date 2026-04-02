import { useState, useEffect } from "react";
import { Save, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { getBranding, updateBranding } from "../api";
import type { BrandingConfig } from "../types";

const DEFAULT_CONFIG: BrandingConfig = {
  company_name: "ATS Domain Review",
  logo_url: "",
  primary_color: "#1a365d",
  accent_color: "#2b6cb0",
  footer_text: "Confidential - Prepared by ATS Domain Review",
};

export default function BrandingSettings() {
  const [config, setConfig] = useState<BrandingConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBranding()
      .then(setConfig)
      .catch(() => {
        /* use defaults */
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await updateBranding(config);
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Failed to save branding settings.");
    } finally {
      setSaving(false);
    }
  };

  const update = (field: keyof BrandingConfig, value: string) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-primary">Branding Settings</h1>
      <p className="text-sm text-gray-500">
        Configure how your reports and exports look.
      </p>

      {/* Form */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
        {/* Company name */}
        <Field label="Company Name">
          <input
            type="text"
            value={config.company_name}
            onChange={(e) => update("company_name", e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
        </Field>

        {/* Logo URL */}
        <Field label="Logo URL">
          <input
            type="text"
            value={config.logo_url}
            onChange={(e) => update("logo_url", e.target.value)}
            placeholder="https://example.com/logo.png"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
          {config.logo_url && (
            <div className="mt-2">
              <img
                src={config.logo_url}
                alt="Logo preview"
                className="h-12 object-contain rounded border border-gray-200 p-1"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            </div>
          )}
        </Field>

        {/* Colors */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Primary Color">
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={config.primary_color}
                onChange={(e) => update("primary_color", e.target.value)}
                className="w-10 h-10 rounded border border-gray-300 cursor-pointer"
              />
              <input
                type="text"
                value={config.primary_color}
                onChange={(e) => update("primary_color", e.target.value)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/40"
              />
            </div>
          </Field>
          <Field label="Accent Color">
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={config.accent_color}
                onChange={(e) => update("accent_color", e.target.value)}
                className="w-10 h-10 rounded border border-gray-300 cursor-pointer"
              />
              <input
                type="text"
                value={config.accent_color}
                onChange={(e) => update("accent_color", e.target.value)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/40"
              />
            </div>
          </Field>
        </div>

        {/* Footer text */}
        <Field label="Footer Text">
          <input
            type="text"
            value={config.footer_text}
            onChange={(e) => update("footer_text", e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
        </Field>

        {/* Error / success */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 text-danger text-sm rounded-lg">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}
        {saved && (
          <div className="flex items-center gap-2 p-3 bg-green-50 text-success text-sm rounded-lg">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            Settings saved successfully.
          </div>
        )}

        {/* Save button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary text-white font-medium rounded-lg hover:bg-primary-light transition-colors disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Settings
          </button>
        </div>
      </div>

      {/* Preview */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-primary mb-4">
          Report Header Preview
        </h2>
        <div
          className="p-6 rounded-lg"
          style={{ backgroundColor: config.primary_color }}
        >
          <div className="flex items-center gap-4">
            {config.logo_url && (
              <img
                src={config.logo_url}
                alt="Logo"
                className="h-10 object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            )}
            <div>
              <h3 className="text-xl font-bold text-white">
                {config.company_name}
              </h3>
              <p className="text-sm" style={{ color: config.accent_color }}>
                Domain Security Assessment
              </p>
            </div>
          </div>
        </div>
        <div className="mt-3 p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-500">{config.footer_text}</p>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}
