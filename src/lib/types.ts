// TypeScript interfaces mirroring the SQLModel definitions in /models.
// These match the JSON shapes returned by the FastAPI backend under /routes.

export type UserType = "parent" | "caregiver" | "individual" | "child";
export type GuardianType = "family" | "personal";
export type StrictnessLevel = "weak" | "normal" | "harsh";
export type RewardType = "gift_card";
export type RelationshipType = "offspring" | "friend" | "supervisor" | "owner";
export type AvailableLanguage =
  | "en"
  | "es"
  | "fr"
  | "de"
  | "it"
  | "pt"
  | "nl"
  | "ru"
  | "zh"
  | "ja"
  | "ko";

export interface CustomWarningMessages {
  warning: string;
  applause: string;
}

// models/models.py :: User
export interface User {
  id: string;
  number_id: number;
  username: string;
  name: string;
  email: string;
  password: string;
  user_type: UserType;
  currency: number;
}

// models/models.py :: UserSettings
export interface UserSettings {
  id: string;
  language: AvailableLanguage;
  user_id: string | null;
}

// models/models.py :: UserHistory
export interface UserHistory {
  id: string;
  user_id: string | null;
}

// models/models.py :: Reward
export interface Reward {
  id: string;
  name: string;
  type: RewardType;
  amount: number;
  cost: number;
}

// models/models.py :: UserWonReward
export interface UserWonReward {
  id: string;
  order_id: number;
  user_id: string | null;
  reward_id: string | null;
}

// models/models.py :: Guardian
export interface Guardian {
  id: string;
  name: string;
  guardian_type: GuardianType;
  owner_id: string | null;
  code: number | null;
  on: boolean;
}

// models/models.py :: GuardianConnection
export interface GuardianConnection {
  id: string;
  guardian_id: string;
  user_id: string;
  user_name: string;
  relationship_with_owner: RelationshipType;
}

// models/models.py :: GuardianSettings
export interface GuardianSettings {
  id: string;
  strictness: StrictnessLevel;
  language: AvailableLanguage;
  custom_warning_messages: CustomWarningMessages;
  points_loss_enabled: boolean;
  base_points_lost: number;
  guardian_id: string | null;
}

// models/models.py :: GuardianRestrictions
export interface GuardianRestrictions {
  id: string;
  guardian_id: string | null;
  restrictions: string[];
}

// models/models.py :: GuardianReport
export interface GuardianReport {
  id: string;
  content: string;
  guardian_id: string | null;
  send_to_id: string | null;
}

// models/models.py :: DeviceID
export interface DeviceID {
  id: string;
  ip_address: string | null;
  user_id: string | null;
}

// models/models.py :: RecentActivity
export interface RecentActivity {
  id: string;
  user_id: string | null;
  activities: unknown[];
}

// models/guardian_session.py :: GuardianSession
export interface GuardianSession {
  id: string;
  user_id: string;
  guardian_id: string;
  warning_active: boolean;
  tracking_start_at: string | null;
  target_duration_seconds: number;
  total_alerts: number;
  penalized_this_episode: boolean;
  events: unknown[];
  points_pending: number;
  last_scan_at: string | null;
  created_at: string;
}

// Response shape from POST /sessions/{session_id}/scan
export interface ScanResult {
  flagged: boolean;
  description: string;
  warning_active: boolean;
  points_awarded: boolean;
}
