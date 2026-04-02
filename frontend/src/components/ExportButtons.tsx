import { FileDown, FileJson, FileSpreadsheet } from "lucide-react";
import { downloadPdf, exportJson, exportCsv } from "../api";

interface ExportButtonsProps {
  scanId: string;
  domain?: string;
}

export default function ExportButtons({ scanId, domain }: ExportButtonsProps) {
  return (
    <div className="flex items-center gap-2 no-print">
      {domain && (
        <button
          onClick={() => downloadPdf(scanId, domain)}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-primary-light transition-colors"
        >
          <FileDown className="w-4 h-4" />
          PDF
        </button>
      )}
      <button
        onClick={() => exportJson(scanId)}
        className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-primary border border-primary rounded-lg hover:bg-primary hover:text-white transition-colors"
      >
        <FileJson className="w-4 h-4" />
        JSON
      </button>
      <button
        onClick={() => exportCsv(scanId)}
        className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-primary border border-primary rounded-lg hover:bg-primary hover:text-white transition-colors"
      >
        <FileSpreadsheet className="w-4 h-4" />
        CSV
      </button>
    </div>
  );
}
