import axios from "axios";
import type {
  ScanResponse,
  ScanStatus,
  DomainReport,
  BrandingConfig,
} from "./types";

const client = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("ats_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function submitDomains(
  domains: string[]
): Promise<ScanResponse> {
  const { data } = await client.post<ScanResponse>("/domains/scan", {
    domains,
  });
  return data;
}

export async function submitEmails(
  emails: string[]
): Promise<ScanResponse> {
  const { data } = await client.post<ScanResponse>("/domains/scan/emails", {
    emails,
  });
  return data;
}

export async function uploadCsv(file: File): Promise<ScanResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post<ScanResponse>(
    "/domains/scan/csv",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function getScanStatus(scanId: string): Promise<ScanStatus> {
  const { data } = await client.get<ScanStatus>(`/domains/scan/${scanId}`);
  return data;
}

export async function getScanResults(
  scanId: string
): Promise<DomainReport[]> {
  const { data } = await client.get<{ scan_id: string; status: string; results: DomainReport[] }>(
    `/domains/scan/${scanId}/results`
  );
  return data.results ?? [];
}

export async function getLatestResult(
  domain: string
): Promise<DomainReport> {
  const { data } = await client.get<DomainReport>(
    `/domains/${encodeURIComponent(domain)}/latest`
  );
  return data;
}

export async function getReportHtml(
  scanId: string,
  domain: string
): Promise<string> {
  const { data } = await client.get<string>(
    `/reports/${scanId}/${encodeURIComponent(domain)}/html`
  );
  return data;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function downloadPdf(scanId: string, domain: string): Promise<void> {
  const { data } = await client.get(
    `/reports/${scanId}/${encodeURIComponent(domain)}/pdf`,
    { responseType: "blob" }
  );
  downloadBlob(data, `${domain}-report.pdf`);
}

export async function exportJson(scanId: string): Promise<void> {
  const { data } = await client.get(
    `/reports/${scanId}/export/json`,
    { responseType: "blob" }
  );
  downloadBlob(data, `scan-${scanId.slice(0, 8)}.json`);
}

export async function exportCsv(scanId: string): Promise<void> {
  const { data } = await client.get(
    `/reports/${scanId}/export/csv`,
    { responseType: "blob" }
  );
  downloadBlob(data, `scan-${scanId.slice(0, 8)}.csv`);
}

export async function getBranding(): Promise<BrandingConfig> {
  const { data } = await client.get<BrandingConfig>("/reports/branding");
  return data;
}

export async function updateBranding(
  config: BrandingConfig
): Promise<BrandingConfig> {
  const { data } = await client.put<{ status: string; branding: BrandingConfig }>(
    "/reports/branding",
    config
  );
  return data.branding;
}

export async function getAuthConfig(): Promise<{ client_id: string; tenant_id: string; enabled: boolean }> {
  const { data } = await client.get("/auth/config");
  return data;
}
