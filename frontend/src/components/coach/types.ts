/**
 * Wire types for the AI Coach + Emergency Pipeline + Notifications.
 *
 * Mirror the shape of `backend/coach/serializers.py`,
 * `backend/emergency/serializers.py` and
 * `backend/notifications/serializers.py`. Keep these literal so a
 * change in the backend contract triggers a TypeScript compile error
 * here instead of a runtime crash later.
 */

export interface CoachConsentPayload {
  ai_coach_local: boolean;
  ai_coach_cloud: boolean;
  share_emergency_contact: boolean;
  cooldown_until: string | null;
  updated_at: string;
}

export type CoachTurnRole = "student" | "assistant" | "system";

export interface CoachTurnPayload {
  id: number;
  turn_number: number;
  role: CoachTurnRole;
  content: string;
  intent: string;
  llm_provider: string;
  llm_model: string;
  refusal_triggered: boolean;
  emergency_triggered: boolean;
  created_at: string;
}

export type CoachConversationStatus = "open" | "ended" | "system_closed";

export interface CoachConversationListItem {
  id: number;
  status: CoachConversationStatus;
  started_at: string;
  ended_at: string | null;
  turn_count: number;
  last_intent: string;
}

export interface CoachConversationDetail extends CoachConversationListItem {
  turns: CoachTurnPayload[];
}

export interface CoachMessageResponse {
  conversation_id: number;
  student_turn: CoachTurnPayload;
  assistant_turn: CoachTurnPayload;
  emergency_triggered: boolean;
  emergency_event_id: number | null;
  refusal_kind: string;
}

export type EmergencySeverity = "medium" | "high" | "critical";
export type EmergencyStatus =
  | "open"
  | "acknowledged"
  | "resolved"
  | "escalated";

export interface EmergencyEventPayload {
  id: number;
  student: { id: number; username: string; display_name: string };
  severity: EmergencySeverity;
  status: EmergencyStatus;
  detected_keywords: string[];
  detector_score: number;
  detected_at: string;
  sla_target_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: number | null;
  resolved_at: string | null;
  resolution_notes: string;
  follow_up_24h_at: string | null;
  follow_up_48h_at: string | null;
  follow_up_72h_at: string | null;
  contacted_emergency_contact: boolean;
}

export interface NotificationPayload {
  id: number;
  channel: "in_app" | "email" | "push";
  severity: "info" | "warning" | "urgent";
  category: string;
  title: string;
  body: string;
  deep_link: string;
  payload: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
  delivered_at: string | null;
}
