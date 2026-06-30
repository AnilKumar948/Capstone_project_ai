import { useMemo, useState } from "react";
import type { Clause, ClauseType } from "../types";

const colorMap: Record<ClauseType, string> = {
  TERMINATION: "bg-indigo-100 text-indigo-800",
  LIABILITY: "bg-red-100 text-red-800",
  CONFIDENTIALITY: "bg-blue-100 text-blue-800",
  PAYMENT: "bg-yellow-100 text-yellow-800",
  INDEMNIFICATION: "bg-orange-100 text-orange-800",
  INTELLECTUAL_PROPERTY: "bg-green-100 text-green-800",
  GOVERNING_LAW: "bg-cyan-100 text-cyan-800",
  DISPUTE_RESOLUTION: "bg-amber-100 text-amber-800",
  FORCE_MAJEURE: "bg-fuchsia-100 text-fuchsia-800",
  WARRANTY: "bg-lime-100 text-lime-800",
  NON_COMPETE: "bg-rose-100 text-rose-800",
  ASSIGNMENT: "bg-teal-100 text-teal-800",
  RENEWAL: "bg-sky-100 text-sky-800",
  NOTICE: "bg-violet-100 text-violet-800",
  GENERAL: "bg-slate-100 text-slate-800",
};

export function ClauseViewer({ clauses }: { clauses: Clause[] }) {
  const [query, setQuery] = useState("");
  const grouped = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return clauses
      .filter((c) => {
        if (!normalizedQuery) return true;
        return c.text.toLowerCase().includes(normalizedQuery) || c.clause_type.toLowerCase().includes(normalizedQuery);
      })
      .reduce<Record<string, Clause[]>>((acc, clause) => {
        acc[clause.clause_type] = acc[clause.clause_type] || [];
        acc[clause.clause_type].push(clause);
        return acc;
      }, {});
  }, [clauses, query]);

  return (
    <section className="space-y-4">
      <h3 className="text-lg font-semibold">Clauses</h3>
      <input
        className="w-full rounded border border-slate-300 px-3 py-2"
        placeholder="Search clause text or type"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {Object.keys(grouped).length === 0 ? <p className="text-sm text-slate-500">No clauses matched this search.</p> : null}
      {Object.entries(grouped).map(([type, items]) => (
        <details key={type} className="rounded border border-slate-200 bg-white p-3">
          <summary className="cursor-pointer font-semibold">{type} ({items.length})</summary>
          <div className="mt-3 space-y-3">
            {items.map((clause, idx) => (
              <article key={`${type}-${idx}`} className="rounded border border-slate-100 p-3">
                <span className={`rounded px-2 py-1 text-xs ${colorMap[clause.clause_type]}`}>{clause.clause_type}</span>
                <p className="mt-2 text-sm text-slate-700">{clause.text}</p>
                <p className="mt-1 text-xs text-slate-500">Confidence: {(clause.confidence * 100).toFixed(0)}%</p>
              </article>
            ))}
          </div>
        </details>
      ))}
    </section>
  );
}
