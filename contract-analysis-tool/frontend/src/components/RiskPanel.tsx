import { useMemo, useState } from "react";
import type { RiskFlag } from "../types";

const levelOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 } as const;
const levelColor = {
  CRITICAL: "border-red-500",
  HIGH: "border-orange-500",
  MEDIUM: "border-yellow-500",
  LOW: "border-slate-400",
} as const;

export function RiskPanel({ risks }: { risks: RiskFlag[] }) {
  const [open, setOpen] = useState<number | null>(null);
  const sorted = useMemo(
    () => [...risks].sort((a, b) => levelOrder[a.risk_level] - levelOrder[b.risk_level]),
    [risks],
  );

  const counts = useMemo(() => {
    return sorted.reduce(
      (acc, risk) => {
        acc[risk.risk_level] += 1;
        return acc;
      },
      { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 },
    );
  }, [sorted]);

  return (
    <section className="space-y-4">
      <h3 className="text-lg font-semibold">Risk Analysis</h3>
      <div className="flex gap-2 text-xs">
        <span>Critical: {counts.CRITICAL}</span>
        <span>High: {counts.HIGH}</span>
        <span>Medium: {counts.MEDIUM}</span>
        <span>Low: {counts.LOW}</span>
      </div>
      <div className="space-y-3">
        {sorted.map((risk, idx) => (
          <article key={`${risk.clause_type}-${idx}`} className={`rounded border-l-4 bg-white p-3 ${levelColor[risk.risk_level]}`}>
            <button className="w-full text-left" onClick={() => setOpen(open === idx ? null : idx)}>
              <p className="font-semibold">{risk.risk_level} - {risk.risk_category}</p>
              <p className="text-sm text-slate-700">{risk.clause_text_snippet}</p>
            </button>
            {open === idx ? (
              <div className="mt-2 text-sm text-slate-700">
                <p>{risk.risk_description}</p>
                <p className="mt-1 font-medium">Recommendation: {risk.recommendation}</p>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
