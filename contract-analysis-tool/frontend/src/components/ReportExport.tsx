import { downloadReport } from "../api/client";

function triggerDownload(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportExport({ reportId }: { reportId: string }) {
  async function handleDownload(format: "json" | "pdf") {
    const blob = await downloadReport(reportId, format);
    triggerDownload(blob, `report-${reportId}.${format}`);
  }

  return (
    <div className="flex gap-2">
      <button className="rounded bg-slate-900 px-3 py-2 text-white" onClick={() => handleDownload("json")}>Download JSON</button>
      <button className="rounded bg-blue-700 px-3 py-2 text-white" onClick={() => handleDownload("pdf")}>Download PDF</button>
    </div>
  );
}
