import axios from "axios";
import type { Report } from "../types";

const TOKEN_STORAGE_KEY = "contract_analysis_access_token";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/",
});

export function getAccessToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function registerUser(email: string, password: string) {
  await apiClient.post("/api/v1/auth/register", { email, password });
}

export async function loginUser(email: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const response = await apiClient.post<{ access_token: string; token_type: string }>("/api/v1/auth/jwt/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  setAccessToken(response.data.access_token);
  return response.data;
}

export async function uploadContract(file: File, onProgress?: (pct: number) => void) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<{ job_id: string; status: string }>("/api/v1/contracts/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (!onProgress || !evt.total) return;
      onProgress(Math.round((evt.loaded * 100) / evt.total));
    },
  });
  return response.data;
}

export async function getReport(reportId: string) {
  const response = await apiClient.get<Report>(`/api/v1/reports/${reportId}`);
  return response.data;
}

export async function getJobStatus(jobId: string) {
  const response = await apiClient.get<{
    job_id: string;
    status: string;
    progress_pct: number;
    created_at: string;
    report_id: string | null;
  }>(`/api/v1/contracts/job/${jobId}`);
  return response.data;
}

export async function downloadReport(reportId: string, format: "json" | "pdf") {
  const response = await apiClient.get(`/api/v1/reports/${reportId}/export?format=${format}`, {
    responseType: "blob",
  });
  return response.data as Blob;
}
