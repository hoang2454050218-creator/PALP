export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "student" | "lecturer" | "admin";
  student_id: string;
  phone: string;
  avatar_url: string;
  consent_given: boolean;
  consent_given_at: string | null;
  created_at: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface Course {
  id: number;
  code: string;
  name: string;
  description: string;
  credits: number;
  concept_count: number;
  milestone_count: number;
}

export interface StudentClass {
  id: number;
  name: string;
  academic_year: string;
  student_count?: number;
  created_at?: string;
}

export interface Enrollment {
  id: number;
  student: number;
  course: Course;
  student_class: number | null;
  semester: string;
  enrolled_at: string;
  is_active: boolean;
}

export interface Concept {
  id: number;
  code: string;
  name: string;
  description: string;
  order: number;
  prerequisite_ids: number[];
}

export interface Milestone {
  id: number;
  title: string;
  description: string;
  order: number;
  target_week: number;
  task_count: number;
}

export interface MilestoneDetail extends Milestone {
  course: number;
  concept_ids: number[];
  tasks: MicroTask[];
}

export interface MicroTaskContent {
  question?: string;
  options?: string[];
  answer?: string;
  explanation?: string;
}

export interface MicroTask {
  id: number;
  milestone: number;
  concept: number;
  concept_name: string;
  title: string;
  description: string;
  task_type: string;
  difficulty: number;
  estimated_minutes: number;
  content: MicroTaskContent | Record<string, unknown>;
  max_score: number;
  order: number;
}

export interface Assessment {
  id: number;
  course: number;
  title: string;
  description: string;
  time_limit_minutes: number;
  question_count: number;
}

export interface AssessmentQuestion {
  id: number;
  concept: number;
  question_type: string;
  text: string;
  options: string[];
  order: number;
  points: number;
}

export interface AssessmentSession {
  id: number;
  assessment: number;
  assessment_title: string;
  status: "in_progress" | "completed" | "abandoned";
  started_at: string;
  completed_at: string | null;
  total_score: number | null;
  total_time_seconds: number | null;
}

export interface LearnerProfile {
  id: number;
  student: number;
  student_name: string;
  course: number;
  overall_score: number;
  initial_mastery: Record<string, number>;
  strengths: number[];
  weaknesses: number[];
  recommended_start_concept: number | null;
  created_at: string;
}

export interface MasteryState {
  id: number;
  concept: number;
  concept_name: string;
  p_mastery: number;
  attempt_count: number;
  correct_count: number;
  last_updated: string;
}

export interface StudentPathway {
  id: number;
  course: number;
  current_concept: number | null;
  current_concept_name: string | null;
  current_milestone: number | null;
  current_milestone_title: string | null;
  current_difficulty: number;
  concepts_completed: number[];
  milestones_completed: number[];
  progress_pct: number;
  updated_at: string;
}

export interface TaskAttempt {
  id: number;
  task: number;
  task_title: string;
  score: number;
  max_score: number;
  duration_seconds: number;
  hints_used: number;
  is_correct: boolean;
  attempt_number: number;
  created_at: string;
}

export interface Alert {
  id: number;
  student: number;
  student_name: string;
  student_username: string;
  student_class: number;
  severity: "green" | "yellow" | "red";
  status: "active" | "dismissed" | "resolved";
  trigger_type: string;
  concept: number | null;
  concept_name: string | null;
  milestone: number | null;
  milestone_title: string | null;
  reason: string;
  evidence: Record<string, unknown>;
  suggested_action: string;
  dismiss_note: string;
  resolved_at: string | null;
  created_at: string;
}

export interface InterventionAction {
  id: number;
  alert: number;
  lecturer: number;
  lecturer_name: string;
  action_type: string;
  target_ids: number[];
  message: string;
  follow_up_status: string;
  created_at: string;
  updated_at: string;
}

export interface ClassOverview {
  total_students: number;
  on_track: number;
  needs_attention: number;
  needs_intervention: number;
  active_alerts: number;
  avg_mastery: number;
  avg_completion_pct: number;
}

export interface PathwayAction {
  action: "supplement" | "advance" | "continue";
  difficulty_adjustment: number;
  p_mastery: number;
  message: string;
  supplementary_content?: Record<string, unknown>;
  next_concept_id?: number | null;
}

export interface ConsentStatus {
  purpose: string;
  label: string;
  description: string;
  granted: boolean;
  last_changed_at: string | null;
  version: string | null;
}

export interface ConsentRecord {
  id: number;
  purpose: string;
  granted: boolean;
  version: string;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  actor: number | null;
  actor_username: string | null;
  action: string;
  target_user: number | null;
  resource: string;
  detail: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface DeletionRequest {
  id: number;
  tiers: string[];
  status: "pending" | "processing" | "completed" | "failed";
  result_summary: Record<string, unknown>;
  requested_at: string;
  completed_at: string | null;
}

export type WellbeingNudgeType = "break_reminder" | "stretch" | "hydrate";
export type WellbeingNudgeResponse = "shown" | "accepted" | "dismissed";

export interface WellbeingNudge {
  id: number;
  nudge_type: WellbeingNudgeType;
  response: WellbeingNudgeResponse;
  continuous_minutes: number;
  created_at: string;
  responded_at: string | null;
}

export interface WellbeingCheckResponse {
  should_nudge: boolean;
  nudge?: WellbeingNudge;
  message?: string;
}

export interface DataExportResponse {
  meta: {
    exported_at: string;
    user_id: number;
    username: string;
    format_version: string;
    glossary: Record<string, string>;
  };
  data: Record<string, unknown>;
}
