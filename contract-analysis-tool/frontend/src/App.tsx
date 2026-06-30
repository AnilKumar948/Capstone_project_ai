import { FormEvent, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import {
  clearAccessToken,
  getReport,
  isAuthenticated,
  loginUser,
  registerUser,
} from "./api/client";
import { ClauseViewer } from "./components/ClauseViewer";
import { DataFields } from "./components/DataFields";
import { JobProgress } from "./components/JobProgress";
import { ReportExport } from "./components/ReportExport";
import { RiskPanel } from "./components/RiskPanel";
import { UploadZone } from "./components/UploadZone";
import type { Report } from "./types";

function RequireAuth({ children }: { children: JSX.Element }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(evt: FormEvent) {
    evt.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await loginUser(email, password);
      navigate("/", { replace: true });
    } catch {
      setError("Login failed. If this is a new account, register first.");
    } finally {
      setBusy(false);
    }
  }

  async function onRegister() {
    setError(null);
    setBusy(true);
    try {
      await registerUser(email, password);
      await loginUser(email, password);
      navigate("/", { replace: true });
    } catch {
      setError("Registration failed. Check email/password and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <form onSubmit={onSubmit} className="w-full max-w-md space-y-4 rounded-2xl border border-slate-300 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Sign In</h1>
        <p className="text-sm text-slate-600">Use your account to upload and view reports.</p>
        <p className="rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
          New user? Enter your email and password, then click Register to continue.
        </p>
        <label className="block space-y-1">
          <span className="text-sm font-medium">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <div className="flex gap-2">
          <button type="submit" disabled={busy} className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50">
            {busy ? "Working..." : "Login"}
          </button>
          <button type="button" disabled={busy} onClick={onRegister} className="rounded bg-blue-700 px-4 py-2 text-white disabled:opacity-50">
            Register
          </button>
        </div>
      </form>
    </main>
  );
}

function HomePage() {
  const navigate = useNavigate();

  function onLogout() {
    clearAccessToken();
    navigate("/login", { replace: true });
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto mb-6 flex max-w-2xl items-center justify-between gap-2">
        <h1 className="text-3xl font-bold">Multi-Modal Contract Analysis Tool</h1>
        <button onClick={onLogout} className="rounded bg-slate-200 px-3 py-2 text-sm font-medium text-slate-800">Logout</button>
      </div>
      <UploadZone />
    </main>
  );
}

function ProgressPage() {
  const { jobId = "" } = useParams();
  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <JobProgress jobId={jobId} />
    </main>
  );
}

function ReportPage() {
  const { reportId = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getReport(reportId).then(setReport);
  }, [reportId]);

  if (!report) {
    return <main className="p-6">Loading report...</main>;
  }

  return (
    <main className="min-h-screen space-y-6 bg-slate-50 p-6">
      <div className="rounded bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-2xl font-semibold">Contract Report</h2>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded bg-slate-200 px-3 py-2 text-sm font-medium text-slate-800"
          >
            Home
          </button>
        </div>
        <p className="text-sm text-slate-600">Job ID: {report.job_id}</p>
        <div className="mt-3">
          <ReportExport reportId={report.report_id} />
        </div>
      </div>
      <DataFields extracted={report.extracted} />
      <RiskPanel risks={report.risks} />
      <ClauseViewer clauses={report.clauses} />
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={(
            <RequireAuth>
              <HomePage />
            </RequireAuth>
          )}
        />
        <Route
          path="/progress/:jobId"
          element={(
            <RequireAuth>
              <ProgressPage />
            </RequireAuth>
          )}
        />
        <Route
          path="/report/:reportId"
          element={(
            <RequireAuth>
              <ReportPage />
            </RequireAuth>
          )}
        />
        <Route path="*" element={<Navigate to={isAuthenticated() ? "/" : "/login"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
