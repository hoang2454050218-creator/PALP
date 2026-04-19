/**
 * Wire types for the Phase 5 intelligence layer:
 * DKT predictions + Knowledge Graph root-cause + Coach memory recall.
 *
 * Mirror the shape of `backend/dkt/serializers.py`,
 * `backend/knowledge_graph/views.py`, `backend/coach_memory/views.py`.
 */

export interface DKTPrediction {
  id: number;
  concept: number;
  concept_name: string;
  concept_code: string;
  model_family: string;
  model_semver: string;
  p_correct_next: number;
  confidence: number;
  explanation: { attention?: Array<{ concept_id: number; weight: number; was_correct: boolean }> };
  sequence_length: number;
  computed_at: string;
}

export interface DKTPredictionsResponse {
  predictions: DKTPrediction[];
}

export interface RootCauseWalkNode {
  concept_id: number;
  name: string;
  p_mastery: number;
  depth: number;
}

export interface RootCauseWalkEdge {
  from_concept: number;
  to_concept: number;
  strength: number;
  dependency_type: string;
}

export interface RootCausePayload {
  target_concept_id: number;
  weakest_prerequisite_id: number | null;
  walk: {
    visited: RootCauseWalkNode[];
    edges: RootCauseWalkEdge[];
    recommendation: string;
    weakest_score: number;
  };
  confidence: number;
  computed_at: string;
}

export interface MemorySemanticItem {
  key: string;
  value: unknown;
  confidence: number;
  source: string;
  updated_at: string;
}

export interface MemoryEpisodicItem {
  kind: string;
  summary: string;
  detail: Record<string, unknown>;
  salience: number;
  occurred_at: string;
}

export interface MemoryProceduralItem {
  strategy_key: string;
  successes: number;
  failures: number;
  effectiveness_estimate: number;
  last_applied_at: string | null;
}

export interface MemoryRecallPayload {
  semantic: MemorySemanticItem[];
  episodic: MemoryEpisodicItem[];
  procedural: MemoryProceduralItem[];
  as_of: string;
}
