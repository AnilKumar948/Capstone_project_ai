import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useJobStatus } from "../hooks/useJobStatus";

export function JobProgress({ jobId }: { jobId: string }) {
  const { progress, step, status, reportId, error } = useJobStatus(jobId);
  const navigate = useNavigate();

  useEffect(() => {
    if (status === "COMPLETE" && reportId) {
      navigate(`/report/${reportId}`);
    }
  }, [status, reportId, navigate]);

  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold">Analyzing Contract</h2>
      <p className="mt-2 text-slate-600">Current step: {step}</p>
      <div className="mt-4 h-3 rounded bg-slate-200">
        <div className="h-full rounded bg-indigo-600 transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-2 text-sm text-slate-700">{progress}%</p>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
