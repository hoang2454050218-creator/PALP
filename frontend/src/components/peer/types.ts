/**
 * Wire types for the Peer Engine API.
 *
 * Mirror the shape of `backend/peer/serializers.py` plus the dataclass
 * outputs of the frontier/benchmark services. Keep these literal so a
 * change in the contract triggers a TypeScript compile error here
 * instead of a runtime crash later.
 */

export interface PeerConsentPayload {
  frontier_mode: boolean;
  peer_comparison: boolean;
  peer_teaching: boolean;
  prompt_shown_at: string | null;
  updated_at: string;
}

export interface FrontierConcept {
  concept_id: number;
  name: string;
  from: number;
  to: number;
  delta: number;
}

export interface FrontierSnapshot {
  lookback_days: number;
  current_avg_mastery: number;
  prior_avg_mastery: number;
  delta: number;
  delta_pct: number;
  concepts_progressed: FrontierConcept[];
  concepts_regressed: FrontierConcept[];
  as_of: string;
}

export type BenchmarkBand =
  | "top_25_pct"
  | "above_median"
  | "below_median"
  | "building_phase"
  | "";

export type BenchmarkReason =
  | "cohort_not_assigned"
  | "cohort_too_small"
  | "";

export interface BenchmarkResult {
  available: boolean;
  reason?: BenchmarkReason;
  cohort_size?: number;
  band?: BenchmarkBand;
  safe_copy?: string;
  encouragement?: string;
}

export interface PeerPartner {
  id: number;
  display_name: string;
}

export interface PeerConcept {
  id: number;
  name: string;
  code: string;
}

export type PeerMatchStatus = "pending" | "active" | "archived" | "declined";

export interface PeerMatch {
  id: number;
  status: PeerMatchStatus;
  compatibility_score: number;
  partner: PeerPartner;
  you_teach: PeerConcept;
  you_learn: PeerConcept;
  created_at: string;
  updated_at: string;
}

export interface BuddyFindResult {
  match: PeerMatch | null;
  message?: string;
}

export interface BuddyMineResult {
  matches: PeerMatch[];
}
