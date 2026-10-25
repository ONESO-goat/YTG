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
  progress: Progress;
}

export type GameEventType = "level_up" | "achievement" | "goal" | "streak" | "freeze_used";

export interface GameEvent {
  type: GameEventType;
  title: string;
  description: string;
  icon: string;
  points: number;
  xp: number;
}

export interface Streak {
  current: number;
  best: number;
  freezes: number;
  max_freezes: number;
  done_today: boolean;
  at_risk: boolean;
}

export interface TodayStats {
  day: string;
  clean_minutes: number;
  goal_minutes: number;
  goal_completed: boolean;
  minute_points: number;
  minute_points_cap: number;
  avoidance_bonuses_left: number;
  points_earned: number;
  points_lost: number;
  xp_earned: number;
  warnings_total: number;
  warnings_heeded: number;
  warnings_ignored: number;
}

export interface Progress {
  level: number;
  title: string;
  xp: number;
  xp_into_level: number;
  xp_for_next_level: number;
  streak: Streak;
  today: TodayStats;
  show_on_leaderboard: boolean;
  timezone: string;
}

export interface Achievement {
  code: string;
  name: string;
  description: string;
  icon: string;
  points: number;
  target: number;
  progress: number;
  unlocked_at: string | null;
}

export interface LeaderboardEntry {
  rank: number;
  name: string;
  username: string;
  level: number;
  weekly_xp: number;
  streak: number;
  is_me: boolean;
}

export interface Leaderboard {
  scope: "family" | "global";
  entries: LeaderboardEntry[];
  me: LeaderboardEntry | null;
  visible: boolean;
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
  purchased_at: string | null;
  refundable_until: string | null;
}

export interface PurchaseResult {
  message: string;
  currency: number;
  events: GameEvent[];
}

export interface ScanResult {
  flagged: boolean;
  description: string;
  category: string | null;
  warning_active: boolean;
  points_awarded: number;
  points_lost: number;
  xp_awarded: number;
  currency: number;
  events: GameEvent[];
  shutdown: boolean;
  idle: boolean;
  analysis_failed: boolean;
}

export interface Health {
  status: string;
  ai_backend: "stub" | "ollama" | "gemini";
}
