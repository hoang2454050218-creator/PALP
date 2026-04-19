/**
 * Wire types for the Direction Engine API.
 *
 * Mirror the shape of `backend/goals/serializers.py` so the frontend
 * stays type-safe without an OpenAPI codegen step. Update both sides
 * when changing the payload.
 */

export interface CareerGoal {
  id: number;
  label: string;
  category: string;
  horizon_months: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface SemesterGoal {
  id: number;
  course: number;
  semester: string;
  mastery_target: number;
  completion_target_pct: number;
  intent: string;
  started_at: string;
  target_end: string | null;
  is_active: boolean;
}

export interface StrategyPlan {
  id: number;
  weekly_goal: number;
  strategy: string;
  rationale: string;
  predicted_minutes: number;
  created_at: string;
}

export interface WeeklyGoal {
  id: number;
  semester_goal: number | null;
  week_start: string;
  target_minutes: number;
  target_concept_ids: number[];
  target_micro_task_count: number;
  status: string;
  drift_pct_last_check: number | null;
  drift_last_checked_at: string | null;
  strategy_plans: StrategyPlan[];
}

export interface GoalReflection {
  id: number;
  weekly_goal: number;
  week_start: string;
  learned_text: string;
  struggle_text: string;
  next_priority_text: string;
  submitted_at: string | null;
}

export interface NorthStarPayload {
  forethought: {
    career_goal: CareerGoal | null;
    semester_goals: SemesterGoal[];
    weekly_goal: WeeklyGoal | null;
  };
  performance: {
    weekly_goal: WeeklyGoal | null;
    drift_pct_last_check: number | null;
  };
  reflection: {
    latest: GoalReflection | null;
  };
}

export interface DailyPlanItem {
  kind: "weak_concept" | "milestone_task" | "variety_review";
  title: string;
  rationale: string;
  micro_task_id: number | null;
  concept_id: number | null;
  estimated_minutes: number | null;
}

export interface DailyPlan {
  date: string;
  weekly_goal_id: number | null;
  items: DailyPlanItem[];
}
