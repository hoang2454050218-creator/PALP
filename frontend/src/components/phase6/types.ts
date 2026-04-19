/**
 * Wire types for Phase 6 — XAI explanations, spaced repetition, copilot.
 *
 * Mirror the shape of the backend serializers in
 * `backend/explainability/views.py`, `backend/spacedrep/views.py`,
 * `backend/instructor_copilot/views.py`.
 */

export interface XaiContribution {
  feature_key: string;
  raw_value: number;
  contribution: number;
  rank: number;
}

export interface XaiCounterfactual {
  feature_key: string;
  current_value: number;
  target_value: number;
  expected_delta: number;
  feasibility: number;
  actionable_hint: string;
}

export interface RiskExplanation {
  id: number;
  kind: string;
  method: string;
  summary: string;
  score: number;
  base_value: number;
  contributions: XaiContribution[];
  counterfactuals: XaiCounterfactual[];
  created_at: string;
}

export type ReviewState =
  | "new"
  | "learning"
  | "review"
  | "relearning"
  | "suspended";

export interface ReviewItem {
  id: number;
  concept_id: number;
  concept_name: string;
  concept_code: string;
  state: ReviewState;
  stability_days: number;
  difficulty: number;
  due_at: string | null;
  last_review_at: string | null;
  review_count: number;
  lapse_count: number;
}

export interface ReviewItemsResponse {
  items: ReviewItem[];
}

export interface ReviewLogResponse {
  item: ReviewItem;
  log: {
    id: number;
    interval_days: number;
    post_stability: number;
    post_difficulty: number;
    retrievability_at_review: number;
    rating: number;
  };
}

export interface GeneratedExercise {
  id: number;
  course_id: number;
  concept_id: number;
  concept_name: string;
  template_key: string;
  difficulty: number;
  title: string;
  body: {
    question: string;
    options: string[];
    correct_answer: string;
    explanation: string;
    hints: string[];
  };
  status: "draft" | "reviewed" | "approved" | "rejected" | "published";
  review_notes: string;
  published_micro_task_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackDraft {
  id: number;
  student_id: number;
  week_start: string;
  summary: string;
  highlights: string[];
  concerns: string[];
  suggestions: string[];
  status: "draft" | "sent" | "archived";
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}
