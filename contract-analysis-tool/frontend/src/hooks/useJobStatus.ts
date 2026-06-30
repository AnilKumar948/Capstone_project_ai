import { useEffect, useState } from "react";
import { getJobStatus } from "../api/client";

export function useJobStatus(jobId: string | null) {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState("Queued");
  const [status, setStatus] = useState("PENDING");
  const [reportId, setReportId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }
    let stopped = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const data = await getJobStatus(jobId);
        if (stopped) {
          return;
        }
        setProgress(data.progress_pct);
        setStatus(data.status);
        if (data.status === "COMPLETE") {
          setStep("Complete");
          if (data.report_id) {
            setReportId(data.report_id);
          }
          return;
        }
        if (data.status === "FAILED") {
          setStep("Failed");
          setError("Analysis failed");
          return;
        }
        setStep(`Processing (${data.progress_pct}%)`);
      } catch {
        if (!stopped) {
          setError("Unable to fetch job status");
        }
      }
      if (!stopped) {
        timer = window.setTimeout(poll, 2000);
      }
    };

    void poll();
    return () => {
      stopped = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [jobId]);

  return { progress, step, status, reportId, error };
}
