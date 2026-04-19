export type ResearchProtocolStatus = "draft" | "approved" | "active" | "closed";
export type ParticipationState = "opted_in" | "withdrawn" | "declined";

export interface ResearchProtocol {
  id: number;
  code: string;
  title: string;
  description: string;
  pi_name?: string;
  pi_email?: string;
  irb_number?: string;
  data_purposes?: string[];
  data_categories?: string[];
  retention_months: number;
  status: ResearchProtocolStatus;
  created_at?: string;
  updated_at?: string;
}

export interface ResearchParticipation {
  id: number;
  protocol: ResearchProtocol;
  state: ParticipationState;
  consent_text_version: string;
  decided_at: string;
  withdrawn_at: string | null;
  notes?: string;
}

export interface ModelCardSummary {
  id: number;
  model_label: string;
  title: string;
  intended_use: string;
  out_of_scope_uses: string[];
  performance: Record<string, unknown>;
  ethical_considerations: string;
  caveats: string;
  licence: string;
  authors: Array<{ name: string; role?: string }>;
  status: "draft" | "reviewed" | "published";
  updated_at?: string;
  published_at?: string | null;
}

export interface BenchmarkResult {
  metric_key: string;
  value: number;
  notes?: string;
}

export interface BenchmarkRun {
  id: number;
  dataset_key: string;
  model_label: string;
  model_family?: string;
  seed: number;
  sample_size: number;
  hyperparameters: Record<string, unknown>;
  status: "pending" | "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  results: BenchmarkResult[];
}
