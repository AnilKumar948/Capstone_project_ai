import type { ExtractedData } from "../types";

function formatDate(value: string | null): string {
  if (!value) return "Not found";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function Field({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <p className="text-xs uppercase text-slate-500">{label}</p>
      <p className="text-sm text-slate-800">{value ?? <span className="text-slate-400">Not found</span>}</p>
    </div>
  );
}

export function DataFields({ extracted }: { extracted: ExtractedData }) {
  return (
    <section className="space-y-3">
      <h3 className="text-lg font-semibold">Extracted Data</h3>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Field label="Effective date" value={formatDate(extracted.effective_date)} />
        <Field label="Expiration date" value={formatDate(extracted.expiration_date)} />
        <Field label="Contract value" value={extracted.contract_value} />
        <Field label="Payment terms" value={extracted.payment_terms} />
        <Field label="Termination notice days" value={extracted.termination_notice_days} />
        <Field label="Liability cap" value={extracted.liability_cap} />
        <Field label="Governing law" value={extracted.governing_law} />
        <div className="rounded border border-slate-200 p-3">
          <p className="text-xs uppercase text-slate-500">Auto renewal</p>
          {extracted.auto_renewal === true ? (
            <span className="rounded bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">Enabled</span>
          ) : extracted.auto_renewal === false ? (
            <span className="text-sm text-slate-600">Disabled</span>
          ) : typeof extracted.auto_renewal === "string" ? (
            <span className="text-sm text-slate-600">{extracted.auto_renewal}</span>
          ) : (
            <span className="text-sm text-slate-400">Not found</span>
          )}
        </div>
      </div>
    </section>
  );
}
