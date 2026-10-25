// Mirrors the response models in models/schemas.py.

export type UserType = "caregiver" | "individual" | "dependent";
export type GuardianType = "family" | "personal" | "dependent";
export type StrictnessLevel = "weak" | "normal" | "harsh";
export type RewardType = "gift_card" | "streak_freeze";
export type RelationshipType = "offspring" | "friend" | "supervisor" | "owner";

export interface User {
  id: string;
  number_id: number;
  username: string;
  name: string;
  email: string;
  user_type: UserType;
  currency: number;
}

export type UserSummary = Omit<User, "email">;

export interface Guardian {
  id: string;
  name: string;
  guardian_type: GuardianType;
  owner_id: string | null;
  on: boolean;
}

export interface Connection {
  id: string;
  guardian_id: string;
  user_id: string;
  user_name: string | null;
  relationship_with_owner: RelationshipType;
}

export interface MonitoringSession {
  id: string;
  user_id: string;
  guardian_id: string;
  active: boolean;
  warning_active: boolean;
  total_alerts: number;
  amount_of_warnings_ignored: number;
  amount_of_warnings_listened: number;
  points_gain_daily_limit: number;
  streak: number;
  last_scan_at: string | null;
  created_at: string;
}

export interface Me {
  user: User;
  guardian: Guardian | null;
  is_guardian_owner: boolean;
  connection: Connection | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface MemberOverview {
  connection: Connection;
  user: UserSummary;
  session: MonitoringSession | null;
}

export interface GuardianSettings {
  strictness: StrictnessLevel;
  warning_message: string;
  applause_message: string;
  reports_enabled: boolean;
  points_loss_enabled: boolean;
  base_points_lost: number;
}

export interface Restrictions {
  default: string[];
  custom: string[];
}

export interface Report {
  id: string;
  content: string;
  guardian_id: string | null;
  send_to_id: string | null;
  updated_at: string;
  created_at: string | null;
}

export interface Reward {
  id: string;
  name: string;
  type: RewardType;
  amount: number;
  cost: number;
}

export interface OwnedReward {
  id: string;
  order_id: number;
  reward: Reward;
}

export interface ScanResult {
  flagged: boolean;
  description: string;
  category: string | null;
  warning_active: boolean;
  points_awarded: number;
  points_lost: number;
  currency: number;
  shutdown: boolean;
  analysis_failed: boolean;
}

export interface Health {
  status: string;
  ai_backend: "stub" | "ollama" | "gemini";
}
