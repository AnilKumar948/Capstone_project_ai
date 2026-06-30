export interface Party {
  name: string;
  jurisdiction: string;
}

export interface Clause {
  clause_type: ClauseType;
  text: string;
  page_hint: number;
  confidence: number;
}

export type ClauseType =
  | "TERMINATION"
  | "LIABILITY"
  | "CONFIDENTIALITY"
  | "PAYMENT"
  | "INDEMNIFICATION"
  | "INTELLECTUAL_PROPERTY"
  | "GOVERNING_LAW"
  | "DISPUTE_RESOLUTION"
  | "FORCE_MAJEURE"
  | "WARRANTY"
  | "NON_COMPETE"
  | "ASSIGNMENT"
  | "RENEWAL"
  | "NOTICE"
  | "GENERAL";

export interface RiskFlag {
  clause_type: string;
  clause_text_snippet: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_category: string;
  risk_description: string;
  recommendation: string;
}

export interface ExtractedData {
  parties: { client: Party; provider: Party; others: Party[] };
  effective_date: string | null;
  expiration_date: string | null;
  auto_renewal: boolean | null;
  contract_value: string | null;
  payment_terms: string | null;
  termination_notice_days: number | null;
  liability_cap: string | null;
  governing_law: string | null;
}

export interface Summary {
  executive_summary: string;
  key_terms: string[];
  unusual_clauses: string[];
  overall_risk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  recommended_actions: string[];
}

export interface Report {
  report_id: string;
  job_id: string;
  clauses: Clause[];
  risks: RiskFlag[];
  extracted: ExtractedData;
  summary: Summary;
  metadata: Record<string, unknown>;
  partial: boolean;
  created_at: string;
}
