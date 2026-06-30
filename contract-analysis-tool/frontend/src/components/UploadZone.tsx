import { FormEvent, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUpload } from "../hooks/useUpload";

const allowed = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
];

export function UploadZone() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { submit, uploadPct, error } = useUpload();
  const navigate = useNavigate();

  const fileMeta = useMemo(() => {
    if (!file) return null;
    return `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB, ${file.type})`;
  }, [file]);

  function onFileSelect(next: File | null) {
    if (!next) return;
    const extension = next.name.split(".").pop()?.toLowerCase() ?? "";
    const extAllowed = ["pdf", "docx", "xlsx", "xls"].includes(extension);
    if (!allowed.includes(next.type) && !extAllowed) {
      alert("Only PDF, DOCX, XLSX, and XLS files are supported.");
      return;
    }
    setFile(next);
  }

  async function onSubmit(evt: FormEvent) {
    evt.preventDefault();
    if (!file || uploading) return;
    setUploading(true);
    try {
      const response = await submit(file);
      if (!response) {
        setUploading(false);
        return;
      }
      navigate(`/progress/${response.job_id}`);
    } catch {
      // Error state is already surfaced by the upload hook.
      setUploading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-2xl space-y-4 rounded-2xl border border-slate-300 bg-white p-6 shadow-sm">
      <div
        className={`rounded-xl border-2 border-dashed p-10 text-center ${dragOver ? "border-blue-500 bg-blue-50" : "border-slate-300"}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          onFileSelect(e.dataTransfer.files[0] ?? null);
        }}
      >
        <p className="text-lg font-semibold">Drop contract file here</p>
        <p className="text-sm text-slate-600">PDF, DOCX, XLSX, or XLS</p>
        <button
          type="button"
          className="mt-4 rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          Choose File
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.xlsx,.xls"
          className="hidden"
          onChange={(e) => onFileSelect(e.target.files?.[0] ?? null)}
        />
      </div>

      {fileMeta ? <p className="text-sm text-slate-700">{fileMeta}</p> : null}
      {uploadPct > 0 ? (
        <div className="h-2 rounded bg-slate-200">
          <div className="h-full rounded bg-blue-600 transition-all" style={{ width: `${uploadPct}%` }} />
        </div>
      ) : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="flex items-center gap-3">
        <button type="submit" disabled={!file || uploading} className="rounded bg-emerald-600 px-4 py-2 text-white disabled:opacity-50">
          {uploading ? "Uploading..." : "Upload Contract"}
        </button>
        {uploading ? (
          <div className="flex items-center gap-2 text-sm text-emerald-700" aria-live="polite">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-emerald-700 border-t-transparent" />
            <span>Uploading in progress</span>
          </div>
        ) : null}
      </div>
    </form>
  );
}
