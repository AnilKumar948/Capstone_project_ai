import { useState } from "react";
import axios from "axios";
import { uploadContract } from "../api/client";

export function useUpload() {
  const [uploadPct, setUploadPct] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function submit(file: File) {
    setError(null);
    setUploadPct(0);
    try {
      return await uploadContract(file, setUploadPct);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === "string") {
          setError(detail);
        } else if (err.response?.status === 401) {
          setError("Please log in to upload contracts");
        } else {
          setError(err.message || "Upload failed");
        }
      } else {
        setError(err instanceof Error ? err.message : "Upload failed");
      }
      return null;
    }
  }

  return { submit, uploadPct, error };
}
